"""
NOTE: This file has been sanitized for portfolio display.
Replace placeholder values with actual credentials for production use.
"""

import json
import os.path
import threading
import traceback
import uuid
from datetime import timedelta
from urllib import parse

from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.utils import timezone
from django.conf import settings

from home import approval, bu_cs, meta, message, task, router
from home.config import constant
from home.enums import ApprovalStatus
from home.gpt import broker, dev_mode, review, dto
from home.models import LarkApprovalInstance, AigcPrompt, IdeaMaterial, LarkUserWorkbench, LarkPoll
from home.tool import poll
from lark.settings import IS_PROD, BASE_DIR
from util import http_util, sys_util, redis_util, sso_util, time_util, s3_util
from util.lark_util import Lark
from util.log_util import logger

# Conditional import for crawler (only when needed)
try:
    from home.crawler import halara_crawler_job
    CRAWLER_AVAILABLE = True
except ImportError:
    logger.warning("Crawler module not available - crawler functionality disabled")
    CRAWLER_AVAILABLE = False


SECRET_DEFAULT = 'WOdGwszKcU0i2y0n'
KEY_SECRET = 'lark-secret'


def auth(request, redirect):
    secret = request.session.get(KEY_SECRET, None)
    if secret is None or secret != SECRET_DEFAULT:
        return 'home/auth.html'
    else:
        return redirect


def index(request):
    redirect_url = sso_util.get_sso_url(constant.HOST)
    hit, login_name, login_id = get_login_user(request)
    if not hit:
        return HttpResponseRedirect(redirect_url)
    context = {}
    return render(request, 'home/index.html', context)


def health(request):
    # approval.get_approval_definition(meta.APPROVAL_CODE_RETURN)
    return HttpResponse('ok')


@csrf_exempt
def event(request):
    data = json.loads(request.body)
    logger.info('[lark event] %s' % data)
    type_ = data.get('type', None)
    challenge = data.get('challenge', '')
    resp = {}

    # 0. if challenge
    if type_ == 'url_verification':
        resp['challenge'] = challenge
        return JsonResponse(resp)

    # 1. judge if task event
    header = data.get('header', None)
    if header is not None and 'event_type' in header and header['event_type'] == 'task.task.updated_v1':
        task.listen_task(data)

    # 2. judge if approval event
    if data is None or 'type' not in data or 'event' not in data:
        return JsonResponse(resp)
    type_ = data['type']
    if type_ != 'event_callback':
        return JsonResponse(resp)
    event_info = data['event']
    if 'type' not in event_info:
        return JsonResponse(resp)
    type_ = event_info['type']

    if type_ == 'approval_instance':
        # approval audit event
        router.approval_event(event_info, raw=data)
    elif type_ == 'message':
        # 线程处理耗时消息
        threading.Thread(target=tackle_chat_msg, args=[event_info, data]).start()

    return JsonResponse(resp)


def tackle_chat_msg(event_info, data):
    # private message
    if event_info.get('chat_type', None) == 'private':
        if event_info.get('text_without_at_bot', None):
            try:
                broker.ask(data)
            except:
                Lark(constant.LARK_CHAT_ID_P0).send_rich_text('chat exception', traceback.format_exc())
            return JsonResponse({})
    # message in chat_group
    message.tackle_message_event(data)


def approval_page(request):
    redirect_url = sso_util.get_sso_url(constant.HOST + 'page/approval')
    hit, login_name, login_id = get_login_user(request)
    if not hit:
        return HttpResponseRedirect(redirect_url)
    to = 'home/approval.html'
    page = auth(request, to)
    if page != to:
        return render(request, page, {})
    instances = LarkApprovalInstance.objects.filter(deleted=0).order_by('-id')[:1000]
    context = {'instances': instances}
    return render(request, page, context)


@csrf_exempt
def ajax_check_approval(request):
    instance_code = request.POST.get('instance_code', None)
    bu_cs.check_approval(instance_code)
    return HttpResponse('ok')


@csrf_exempt
def ajax_login(request):
    secret = request.POST.get('secret', None)
    if secret == SECRET_DEFAULT:
        request.session[KEY_SECRET] = secret
    return HttpResponse('ok')


def approval_instance(request):
    resp = None
    instance_code = request.GET.get('instance_code', None)
    if instance_code is not None:
        resp = approval.get_approval_instance(instance_code)
    return JsonResponse(resp)


@csrf_exempt
def cancel_approval(request):
    data = json.loads(request.body)
    logger.info('[approval cancel request] %s' % data)
    instance_id = data.get('approvalId', None)
    if instance_id is None:
        return http_util.wrap_err_response(-1, 'empty approvalId')
    instance = LarkApprovalInstance.objects.filter(instance_code=instance_id, deleted=0).first()
    if instance is None:
        return http_util.wrap_err_response(-1, 'not found this approvalId')

    if instance.approval_status != ApprovalStatus.PENDING.value:
        return http_util.wrap_err_response(-1, 'cannot cancel with this status: %s' %
                                           meta.MAP_APPROVAL_STATUS_DISPLAY.get(ApprovalStatus(instance.approval_status), ''))
    resp = approval.cancel_approval(instance.approval_code, instance_id, instance.submitter)
    return http_util.wrap_ok_response(resp)


@csrf_exempt
def check_pending(request):
    data = json.loads(request.body)
    logger.info('[approval check pending request] %s' % data)
    approval_ids = data.get('approvalIds', [])
    result = {'differ': []}
    arg_list = []
    if approval_ids is not None and len(approval_ids) > 0:
        instances = LarkApprovalInstance.objects.filter(instance_code__in=approval_ids)
        if len(instances) > 0:
            for instance in instances:
                if instance.approval_status != ApprovalStatus.PENDING.value:
                    result['differ'].append(instance.instance_code)
                    # add to check notify
                    arg_list.append(instance.instance_code)

    if len(arg_list) > 0:
        sys_util.multi_threads(7, bu_cs.check_approval, arg_list, wait=False)
    return http_util.wrap_ok_response(result)


def just_print(raw):
    print(raw)


def page_404(request):
    return render(request, 'home/404.html', {})


def get_login_user(request):
    hit = True
    login_name = '游客'
    # my: dac53d12
    login_id = ''
    # 生产环境需要飞书登录
    if IS_PROD:
        token = request.session.get(constant.SESSION_KEY_SSO_TOKEN, None)
        if not token:
            hit = False
            return hit, login_name, login_id
        # 查找缓存
        cache_key = 'sso:token:{}'.format(token)
        login_user = redis_util.get(cache_key)
        if login_user and len(login_user.split('::')) >= 2:
            items = login_user.split('::')
            login_name = items[0]
            login_id = items[1]
        else:
            hit, user_info = sso_util.get_user_info(token)
            if not hit:
                hit = False
                return hit, login_name, login_id
            login_name = user_info['name']
            login_id = user_info['user_id']
            redis_util.set_(cache_key, '{}::{}'.format(login_name, login_id), 24 * 3600)
    return hit, login_name, login_id


@csrf_exempt
def sso_callback(request):
    redirect_url = '/'
    code = request.GET.get('code', None)
    state = request.GET.get('state', '')
    # 0. 判断是否需要转发
    obj_host = state.replace('https://', '').split('/')[0]
    obj_host = f'https://{obj_host}/'
    if obj_host != constant.HOST:
        # 转发
        params = request.GET.copy()
        return HttpResponseRedirect(f'{obj_host}callback/sso?{parse.urlencode(params)}')
    else:
        # 1. 解析token
        hit, token = sso_util.get_access_token(code)
        if not hit:
            Lark(constant.LARK_CHAT_ID_P0).send_rich_text('code parse error', token)
            return HttpResponseRedirect(constant.ERROR_PAGE_404)
        # 2. 将token写入session
        request.session[constant.SESSION_KEY_SSO_TOKEN] = token
    # 3. 重定向页面
    if state:
        redirect_url = state
    return HttpResponseRedirect(redirect_url)


def chatgpt_index(request):
    context = {}
    return render(request, 'home/chatgpt/index.html', context)


def chatgpt_prompt(request):
    redirect_url = sso_util.get_sso_url(constant.HOST + 'page/chatgpt/prompt')
    hit, login_name, login_id = get_login_user(request)
    if not hit:
        return HttpResponseRedirect(redirect_url)
    context = {'login_name': login_name, 'login_id': login_id}
    return render(request, 'home/chatgpt/prompt.html', context)


def chatgpt_prompt_manage(request, prompt_type=dev_mode.CHATGPT_SYSTEM_PROMPT):
    redirect_url = sso_util.get_sso_url(constant.HOST + 'page/chatgpt/prompt/manage')
    hit, login_name, login_id = get_login_user(request)
    if not hit:
        return HttpResponseRedirect(redirect_url)
    prompts = AigcPrompt.objects.filter(prompt_type=prompt_type, scope_type='lark-user', scope_id=login_id, deleted=constant.NO_IN_DB).order_by('id').all()
    context = {'login_name': login_name, 'login_id': login_id, 'prompt_type': prompt_type, 'prompts': prompts}
    return render(request, 'home/chatgpt/prompt_manage.html', context)


def tool(request):
    context = {}
    return render(request, 'home/tool.html', context)


def tool_speech2text(request):
    redirect_url = sso_util.get_sso_url(constant.HOST + 'page/tool/speech2text')
    hit, login_name, login_id = get_login_user(request)
    if not hit:
        return HttpResponseRedirect(redirect_url)
    context = {}
    return render(request, 'home/tool_speech_text.html', context)


def page_idea_index(request):
    return render(request, 'home/idea_index.html', {})


def page_idea_list(request):
    redirect_url = sso_util.get_sso_url(constant.HOST + 'page/idea/list')
    hit, login_name, login_id = get_login_user(request)
    if not hit:
        return HttpResponseRedirect(redirect_url)
    # get ideas
    ideas = []
    if login_id:
        records = IdeaMaterial.objects.using('material').filter(material_type='video', user_id_create=login_id, deleted=0).order_by('-updated_at').all()
        for each in records:
            post_at = (time_util.get_cnt_from_timestamp(each.post_at) + timedelta(hours=8)).strftime(time_util.TIME_FORMAT_DEFAULT)
            update_at = (each.updated_at + timedelta(hours=8)).strftime(time_util.TIME_FORMAT_DEFAULT)
            if each.detail:
                essay = each.detail.get('essay', '')
            else:
                essay = ''
            ideas.append({'id': each.id, 'video': each.material_url, 'cover': each.cover_url,
                          'source': each.material_source, 'author': each.post_user_name, 'post_at': post_at,
                          'like': each.like_count, 'comment': each.comment_count, 'collect': each.collect_count,
                          'share': each.share_count, 'update_at': update_at, 'essay': essay, 'page_url': each.page_url})
    context = {'login_id': login_id, 'login_name': login_name, 'ideas': ideas}
    return render(request, 'home/idea_list.html', context)


def page_chatgpt_review(request):
    redirect_url = sso_util.get_sso_url(constant.HOST + 'page/chatgpt/review')
    hit, login_name, login_id = get_login_user(request)
    if not hit:
        return HttpResponseRedirect(redirect_url)
    disabled = login_id != constant.LARK_USER_ID_LUKE
    use_sys_prompt = True
    # get workbench data
    reviews_count, file_name, excel_columns, review_format = 0, '', review.DEFAULT_EXCEL_COLUMNS, review.DEFAULT_REVIEW_FORMAT
    ask_prompt, merge_prompt, system_prompt = review.DEFAULT_ASK_PROMPT, review.DEFAULT_MERGE_PROMPT, review.DEFAULT_SYS_PROMPT
    auto_merge, temperature, words_batch = review.DEFAULT_AUTO_MERGE, review.DEFAULT_TEMPERATURE, review.DEFAULT_WORDS_BATCH
    record = LarkUserWorkbench.objects.filter(lark_user_id=login_id, work_symbol=dto.WORK_SYMBOL).first()
    if record and record.detail:
        reviews_count = len(record.detail.get(dto.JSON_KEY_EXCEL_DATA, []))
        file_name = record.detail.get(dto.JSON_KEY_EXCEL_NAME, file_name)
        excel_columns = record.detail.get(dto.JSON_KEY_EXCEL_COLUMNS, excel_columns)
        review_format = record.detail.get(dto.JSON_KEY_REVIEW_FORMAT, review_format)
        system_prompt = record.detail.get(dto.JSON_KEY_SYS_PROMPT, system_prompt)
        auto_merge = record.detail.get(dto.JSON_KEY_AUTO_MERGE, auto_merge)
        temperature = record.detail.get(dto.JSON_KEY_TEMPERATURE, temperature)
        words_batch = min(record.detail.get(dto.JSON_KEY_WORDS_BATCH, words_batch), review.MAX_WORDS_BATCH)
        if not use_sys_prompt:
            ask_prompt = record.detail.get(dto.JSON_KEY_ASK_PROMPT, ask_prompt)
            merge_prompt = record.detail.get(dto.JSON_KEY_MERGE_PROMPT, merge_prompt)

    context = {'login_id': login_id, 'login_name': login_name, 'reviews_count': reviews_count, 'file_name': file_name,
               'temperature': temperature, 'words_batch': words_batch, 'words_batch_max': review.MAX_WORDS_BATCH,
               'excel_columns': excel_columns, 'review_format': review_format, 'ask_prompt': ask_prompt,
               'merge_prompt': merge_prompt, 'system_prompt': system_prompt, 'auto_merge': auto_merge, 'disabled': disabled,
               'default_obj_desc': review.DEFAULT_OBJ_DESC, 'default_tips': review.DEFAULT_TIPS,
               'prompt_cons': review.PROMPT_CONS, 'prompt_scenario': review.PROMPT_SCENARIO, 'sys_ask': review.DEFAULT_ASK_PROMPT.replace('\n', '&#13;'),
               'sys_merge': review.DEFAULT_MERGE_PROMPT.replace('\n', '&#13;'), 'prompt_common': review.PROMPT_COMMON,
               'prompt_pros': review.PROMPT_PROS}
    return render(request, 'home/chatgpt/review.html', context)


def page_tool_words(request):
    context = {}
    return render(request, 'home/tool_words.html', context)


def page_tool_detect(request):
    context = {}
    return render(request, 'home/tool_detect.html', context)


@csrf_exempt
def upload_file(request):
    data = request.body
    header = request.headers
    file_name = header.get('Filename', '')
    unique_code = str(uuid.uuid4())[:6]
    path = str(BASE_DIR) + '/home/data/tmp/' + f'{unique_code}-{file_name}'
    with open(path, 'wb') as f:
        f.write(data)
    s3_client = s3_util.S3Client()
    content_type = 'text/plain'
    if 'png' in file_name or 'jpeg' in file_name or 'image' in file_name:
        content_type = 'image/png'
    elif 'mp4' in file_name:
        content_type = 'video/mp4'
    elif 'xlsx' in file_name or 'xls' in file_name:
        content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    s3_url = s3_client.upload_file(s3_util.DEFAULT_BUCKET, f'lark/upload/{unique_code}-{file_name}', path, content_type)
    if path and os.path.exists(path):
        os.remove(path)
    return http_util.wrap_ok_response({'s3_url': s3_url})


def mbti(request):
    redirect_url = sso_util.get_sso_url(constant.HOST + 'page/poll/mbti')
    hit, login_name, login_id = get_login_user(request)
    if not hit:
        return HttpResponseRedirect(redirect_url)
    # check if polled
    record = LarkPoll.objects.filter(poll_type=poll.POLL_TYPE, lark_user=login_id, repoll=constant.NO_IN_DB).first()
    if not record:
        items = poll.QUESTIONS
        context = {'items': items, 'size': len(items), 'login_name': login_name, 'login_id': login_id}
        return render(request, 'home/poll/mbti.html', context)
    else:
        table_data = []
        result = record.result
        map_score = result['score']
        for pair in poll.PAIRS:
            table_data.append([f'{pair[0]} ({poll.MAP_FACTOR[pair[0]]})', f'{pair[1]} ({poll.MAP_FACTOR[pair[1]]})'])
            table_data.append([f'{map_score[pair[0]]}', f'{map_score[pair[1]]}'])
        context = {'mbti': result['mbti'], 'desc': result['desc'], 'score': table_data, 'login_name': login_name,
                   'login_id': login_id}
        return render(request, 'home/poll/mbti_result.html', context)


@csrf_exempt
def cal_mbti(request):
    data = json.loads(request.body)
    logger.info('[cal mbti] %s' % data)
    options = data.get('options', [])
    login_id = data.get('login_id', None)
    try:
        ok, tips = poll.calculate_mbti(login_id, options)
        if ok:
            return http_util.wrap_ok_response(tips)
        else:
            return http_util.wrap_err_response(-1, tips)
    except:
        Lark(constant.LARK_CHAT_ID_P0).send_rich_text('cal mbti error', traceback.format_exc())
        logger.error('[cal mbti error] {}'.format(traceback.format_exc()))
        return http_util.wrap_err_response(-1, 'exception')


@csrf_exempt
def handle_excel_file(request):
    """Handle Excel file uploads from Lark"""
    resp = {'code': 0, 'msg': '', 'data': {}}
    try:
        file_raw = request.FILES.get('file')
        if not file_raw:
            return http_util.wrap_err_response(-1, 'No file provided')
            
        # Save file temporarily
        file_name = str(file_raw)
        local_file = f'{str(BASE_DIR)}/home/gpt/data/tmp/{file_name}'
        os.makedirs(os.path.dirname(local_file), exist_ok=True)
        
        with open(local_file, 'wb') as f:
            f.write(file_raw.read())
            
        # Process Excel file
        excel_handler = ExcelHandler()
        success, message = excel_handler.read_excel(local_file)
        
        # Clean up
        os.remove(local_file)
        
        if not success:
            return http_util.wrap_err_response(-1, message)
            
        resp['data']['summary'] = message
        return JsonResponse(resp)
        
    except Exception as e:
        logger.error(f'Error handling Excel file: {str(e)}')
        return http_util.wrap_err_response(-1, f'Failed to process Excel file: {str(e)}')


def test_crawler(request):
    """Test endpoint to manually trigger the crawler"""
    if not CRAWLER_AVAILABLE:
        return JsonResponse({
            'status': 'error',
            'message': 'Crawler module not available'
        }, status=500)
    
    try:
        halara_crawler_job.run_crawler()
        return JsonResponse({
            'status': 'success',
            'message': 'Crawler executed successfully'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

