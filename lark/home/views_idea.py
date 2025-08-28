import json
import traceback

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from home import message
from home.config import constant
from home.idea_bot import broker
from home.models import IdeaMaterial
from util import http_util
from util.lark_util import Lark
from util.log_util import logger


@csrf_exempt
def event(request):
    data = json.loads(request.body)
    logger.info('[lark idea_bot event] %s' % data)
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
            broker.tackle_event(lark_event)
        except:
            logger.error('[idea_bot event] tackle exception: {}'.format(traceback.format_exc()))
            Lark(constant.LARK_CHAT_ID_P0).send_rich_text('idea_bot event tackle exception', traceback.format_exc())
    else:
        logger.error('[idea_bot event] parse failed: {}'.format(data))
        Lark(constant.LARK_CHAT_ID_P0).send_rich_text('idea_bot event parse failed', json.dumps(data))

    return JsonResponse(resp)


@csrf_exempt
def del_idea(request):
    data = json.loads(request.body)
    logger.info('[idea del] %s' % data)
    user_id = data.get('userId', None)
    idea_id = data.get('ideaId', None)
    if user_id and idea_id:
        record = IdeaMaterial.objects.using('material').filter(id=idea_id).first()
        if record:
            if record.user_id_update != user_id:
                return JsonResponse(http_util.wrap_err_response(-1, 'no authorized'))
            record.deleted = constant.YES_IN_DB
            record.save()
    return http_util.wrap_ok_response(None)


@csrf_exempt
def idea_essay(request):
    data = json.loads(request.body)
    logger.info('[idea essay] %s' % data)
    user_id = data.get('userId', None)
    idea_id = data.get('ideaId', None)
    essay = data.get('essay', '')
    if user_id and idea_id:
        record = IdeaMaterial.objects.using('material').filter(id=idea_id).first()
        if record:
            detail = record.detail
            if not detail:
                detail = {}
            old_essay = detail.get('essay', '')
            if old_essay != essay:
                detail['essay'] = essay
                record.user_id_update = user_id
                record.detail = detail
                record.save()
    return http_util.wrap_ok_response(None)

