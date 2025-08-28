import json
import os
import threading
import traceback

import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from home import redis_key, message
from home.client import lukas_client
from home.config import constant
from home.gpt.cache import get_chatgpt4_users
from home.gpt.review import RequestRunReview, RequestMergeReview
from home.gpt.review_reader.enums import ExtractType
from home.models import AigcPrompt
from lark.settings import BASE_DIR, IS_PROD
from util import redis_util, http_util
from util.lark_util import Lark
from util.log_util import logger
from home.gpt import chat_client as gpt_client, speech_client, dev_mode, review, manual_tackle
from home.gpt import cache as gpt_cache


@csrf_exempt
def gpt_ask(request):
    data = json.loads(request.body)
    logger.info('[chatGPT ask] %s' % data)
    system_prompt = data.get('systemPrompt', None)
    user_prompt = data.get('userPrompt', None)
    model = data.get('model', None)
    resp = {'code': 0, 'msg': '', 'data': {'hit': False, 'reply': ''}}
    if not user_prompt:
        return JsonResponse(resp)
    prompt_list = ['user::{}'.format(user_prompt.strip())]
    if not system_prompt:
        system_prompt = ''
    hit, reply = gpt_client.ask(prompt_list, system_prompt=system_prompt.strip(), model=model)
    resp['data']['reply'] = reply
    resp['data']['hit'] = hit
    logger.info('[chatGPT reply] %s' % reply)

    return JsonResponse(resp)


@csrf_exempt
def add_tone(request):
    data = json.loads(request.body)
    logger.info('[chatGPT add tone] %s' % data)
    user_id = data.get('userId', None)
    tone_title = data.get('toneTitle', None)
    system_prompt = data.get('systemPrompt', None)
    resp = {'code': 0, 'msg': '', 'data': {}}
    if IS_PROD and (not user_id or user_id == '0'):
        resp['code'] = -1
        resp['msg'] = 'Not login, pls refresh page'
        return JsonResponse(resp)
    if not system_prompt:
        resp['code'] = -1
        resp['msg'] = 'Pls input system_prompt as tone content'
        return JsonResponse(resp)
    if not tone_title:
        resp['code'] = -1
        resp['msg'] = 'Pls input tone title'
        return JsonResponse(resp)
    # 执行写入
    prompt_type = dev_mode.CHATGPT_SYSTEM_PROMPT
    scope_type = dev_mode.SCOPE_LARK_USER
    detail = {'text': system_prompt}
    # 判断是否已经存在
    overlap_key = 'lock:chatgpt:tone:add:{}'.format(user_id)
    record = AigcPrompt.objects.filter(prompt_type=prompt_type, scope_type=scope_type, scope_id=user_id, title=tone_title).first()
    if record:
        if redis_util.set_nx(overlap_key, 30):
            resp['code'] = -1
            resp['msg'] = '同标题记录已经存在，是否覆盖或换标题？\n（继续点击提交将执行覆盖旧记录）'
            return JsonResponse(resp)
        else:
            record.detail = detail
            record.user_id_update = user_id
            record.deleted = 0
            redis_util.del_(overlap_key)
    else:
    # 直接创建
        record = AigcPrompt(prompt_type=prompt_type, scope_type=scope_type, scope_id=user_id, title=tone_title,
                            prompt_topic='', detail=detail, user_id_create=user_id, user_id_update=user_id, deleted=0)

    record.save()
    return JsonResponse(resp)


@csrf_exempt
def del_prompt(request):
    data = json.loads(request.body)
    logger.info('[chatGPT del prompt] %s' % data)
    user_id = data.get('userId', None)
    prompt_id = data.get('promptId', None)
    resp = {'code': 0, 'msg': '', 'data': {}}
    if not prompt_id:
        resp['code'] = -1
        resp['msg'] = 'empty promptId'
        return JsonResponse(resp)
    prompt = AigcPrompt.objects.filter(id=prompt_id).first()
    if not prompt:
        resp['code'] = -1
        resp['msg'] = 'not exist prompt'
        return JsonResponse(resp)
    if prompt.prompt_type == dev_mode.CHATGPT_SYSTEM_PROMPT:
        ok, msg = gpt_cache.del_tone(user_id, prompt_id)
    elif prompt.prompt_type == dev_mode.CHATGPT_USER_PROMPT:
        ok, msg = dev_mode.del_recipe(user_id, prompt_id)
    else:
        ok, msg = False, 'not support prompt_type'
    resp['msg'] = msg
    if not ok:
        resp['code'] = -1
    return JsonResponse(resp)


@csrf_exempt
def tool_speech2text_receive(request):
    resp = {'code': 0, 'msg': '', 'data': {}}
    file_raw = request.FILES['fileToUpload']
    file_name = str(file_raw)
    local_file = str(BASE_DIR) + '/home/gpt/data/{}'.format(file_name)
    with open(local_file, 'wb') as f:
        f.write(file_raw.read())
    ok, text = speech_client.to_text(file_path=local_file)
    if not ok:
        resp['code'] = -1
        resp['msg'] = text
    else:
        resp['data']['text'] = text
    logger.info('[speech to text] file upload: {}, ok: {}, result: {}'.format(file_name, ok, text))
    os.remove(local_file)
    return JsonResponse(resp)


@csrf_exempt
def add_recipe(request):
    data = json.loads(request.body)
    logger.info('[chatGPT add recipe] %s' % data)
    user_id = data.get('userId', None)
    recipe_title = data.get('recipeTitle', None)
    user_prompt = data.get('userPrompt', None)
    resp = {'code': 0, 'msg': '', 'data': {}}
    if IS_PROD and (not user_id or user_id == '0'):
        resp['code'] = -1
        resp['msg'] = 'Not login, pls refresh page'
        return JsonResponse(resp)
    if not user_prompt:
        resp['code'] = -1
        resp['msg'] = 'Pls input ask as recipe content'
        return JsonResponse(resp)
    if not recipe_title:
        resp['code'] = -1
        resp['msg'] = 'Pls input recipe title'
        return JsonResponse(resp)
    # 执行写入
    prompt_type = dev_mode.CHATGPT_USER_PROMPT
    scope_type = dev_mode.SCOPE_LARK_USER
    detail = {'text': user_prompt}
    # 判断是否已经存在
    overlap_key = 'lock:chatgpt:recipe:add:{}'.format(user_id)
    record = AigcPrompt.objects.filter(prompt_type=prompt_type, scope_type=scope_type, scope_id=user_id, title=recipe_title).first()
    if record:
        if redis_util.set_nx(overlap_key, 30):
            resp['code'] = -1
            resp['msg'] = '同标题记录已经存在，是否覆盖或换标题？\n（继续点击提交将执行覆盖旧记录）'
            return JsonResponse(resp)
        else:
            record.detail = detail
            record.user_id_update = user_id
            record.deleted = 0
            redis_util.del_(overlap_key)
    else:
        # 直接创建
        record = AigcPrompt(prompt_type=prompt_type, scope_type=scope_type, scope_id=user_id, title=recipe_title,
                            prompt_topic='', detail=detail, user_id_create=user_id, user_id_update=user_id, deleted=0)

    record.save()
    return JsonResponse(resp)


@csrf_exempt
def chatgpt_review_upload(request):
    resp = {'code': 0, 'msg': '', 'data': {}}
    file_raw = request.FILES['fileToUpload']
    columns = request.POST['columns']
    user_id = request.POST['userId']
    ok, reviews = review.tackle_excel(user_id, file_raw, columns)
    if not ok:
        resp['code'] = -1
        resp['msg'] = reviews
    else:
        resp['data']['reviews_count'] = len(reviews)
    return JsonResponse(resp)


@csrf_exempt
def chatgpt_review_run(request):
    resp_data = {}
    data = json.loads(request.body)
    logger.info('[chatGPT review run] %s' % data)
    req = RequestRunReview()
    req.user_id = data.get('userId', None)
    if not redis_util.set_nx(redis_key.lock_chatgpt_review_run(req.user_id), 60*60):
        return http_util.wrap_err_response(-1, 'task still running, pls wait for a while')
    req.review_format = data.get('reviewFormat', None)
    req.ask_prompt = data.get('askPrompt', None)
    req.merge_prompt = data.get('mergePrompt', None)
    req.system_prompt = data.get('systemPrompt', None)
    req.temperature = float(data.get('temperature', 0))
    req.auto_merge = data.get('autoMerge', False)
    req.use_lark = data.get('useLark', False)
    req.max_segments = int(data.get('maxSegments', 0))
    req.words_batch = int(data.get('wordsBatch', review.MAX_WORDS_BATCH))
    # todo hack
    if 'Cons(' in req.ask_prompt:
        req.extract_type = ExtractType.CONS
    elif 'Dressing-Scenario(' in req.ask_prompt:
        req.extract_type = ExtractType.SCENARIO
    elif 'of Main Ideas' in req.ask_prompt:
        req.extract_type = ExtractType.COMMON
    elif 'Pros(' in req.ask_prompt:
        req.extract_type = ExtractType.PROS
    threading.Thread(target=review.run_review, args=[req]).start()
    # for i in range(len(replies)):
    #     resp_data['reply{}'.format(i+1)] = replies[i]

    return http_util.wrap_ok_response(resp_data)


@csrf_exempt
def chatgpt_review_merge(request):
    resp_data = {}
    data = json.loads(request.body)
    logger.info('[chatGPT review merge] %s' % data)
    req = RequestMergeReview()
    req.user_id = data.get('userId', None)
    if not redis_util.set_nx(redis_key.lock_chatgpt_review_merge(req.user_id), 60*60):
        return http_util.wrap_err_response(-1, 'task still running, pls wait for a while')
    req.replies = data.get('replies', None)
    req.merge_prompt = data.get('mergePrompt', None)
    req.system_prompt = data.get('systemPrompt', None)
    req.temperature = float(data.get('temperature', 0))
    req.use_lark = data.get('useLark', False)
    threading.Thread(target=review.merge_replies_by_chatgpt, args=[req]).start()
    # if not reply:
    #     reply = 'failed to get any result'
    # resp_data['reply'] = reply
    return http_util.wrap_ok_response(resp_data)


@csrf_exempt
def chatgpt_manual_merge(request):
    data = json.loads(request.body)
    logger.info('[chatGPT review manual merge] %s' % data)
    threading.Thread(target=manual_tackle.manual_merge).start()
    return http_util.wrap_ok_response({})


@csrf_exempt
def chatgpt_manual_trim(request):
    data = json.loads(request.body)
    logger.info('[chatGPT review manual trim] %s' % data)
    reply = data.get('reply', None)
    if not reply:
        return http_util.wrap_err_response(-1, 'empty reply')
    threading.Thread(target=manual_tackle.manual_trim, args=[reply]).start()
    return http_util.wrap_ok_response({})


@csrf_exempt
def chatgpt_gpt4_users(request):
    data = json.loads(request.body)
    logger.info('[chatGPT gpt4 users] %s' % data)
    refresh = data.get('refresh', False)
    users = get_chatgpt4_users(force_update=refresh)
    return http_util.wrap_ok_response({'total': len(users), 'users': users})


@csrf_exempt
def event_obs(request):
    data = json.loads(request.body)
    logger.info('[lark Obs event] %s' % data)
    type_ = data.get('type', None)
    challenge = data.get('challenge', '')
    resp = {}
    # 0. if challenge
    if type_ == 'url_verification':
        resp['challenge'] = challenge
        return JsonResponse(resp)

    # 1. event parse
    hit, lark_event = message.parse_event_schema_2(data)
    if hit:
        try:
            url = 'https://your-domain.com'
            retry, retry_max = 0, 2
            while retry < retry_max:
                retry += 1
                transfer_resp = requests.post(url, headers=http_util.get_json_headers(), data=json.dumps(lark_event.to_json()))
                logger.info('[Obs event] transfer response: {}'.format(transfer_resp))
                if transfer_resp and transfer_resp.ok:
                    break
        except:
            logger.error('[Obs event] tackle exception: {}'.format(traceback.format_exc()))
            Lark(constant.LARK_CHAT_ID_P0_LUKE).send_rich_text('Obs event tackle exception', traceback.format_exc())
    else:
        logger.error('[Obs event] parse failed: {}'.format(data))
        Lark(constant.LARK_CHAT_ID_P0_LUKE).send_rich_text('Obs event parse failed', json.dumps(data))

    return JsonResponse(resp)


@csrf_exempt
def tackle_words_split(request):
    data = json.loads(request.body)
    logger.info('[tool tackle words] %s' % data)
    raw = data.get('raw', None)
    split = data.get('split', ';')
    if not raw:
        return http_util.wrap_ok_response({'result': ''})
    map_key_count = {}
    items = raw.strip().split('\n')
    for item in items:
        keys = item.strip().split(split)
        for key in keys:
            key = key.strip()
            if not key:
                continue
            if key not in map_key_count:
                map_key_count[key] = 0
            map_key_count[key] += 1
    list_result = [{'key': x, 'count': y} for x, y in map_key_count.items()]
    list_result.sort(key=lambda x: x['count'], reverse=True)
    result = ''
    for each in list_result:
        result += f'{each["key"]}\t{each["count"]}\n'
    result = result.strip()
    return http_util.wrap_ok_response({'list_result': list_result, 'str_result': result})


@csrf_exempt
def tackle_detect_face(request):
    data = json.loads(request.body)
    logger.info('[tool tackle detect] %s' % data)
    pic_url = data.get('pic_url', None)
    ad_id = data.get('ad_id', None)
    fb_url = data.get('fb_url', None)
    result, raw_url = 'Not Found', ''
    if resp := lukas_client.detect_face(pic_url=pic_url, ad_id=ad_id, fb_url=fb_url):
        result = resp['result']
        raw_url = resp['raw_url']

    return http_util.wrap_ok_response({'result': result, 'raw_url': raw_url})

