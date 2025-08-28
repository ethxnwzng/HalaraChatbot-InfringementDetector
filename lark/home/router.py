import traceback
from home import meta, bu_cs, kafka_api
from util.log_util import logger


APPROVALS_CS = [meta.APPROVAL_CODE_RETURN, meta.APPROVAL_CODE_REFUND, meta.APPROVAL_CODE_DISCOUNT]


def approval_event(event, raw=None):
    if 'type' not in event or 'status' not in event or 'operate_time' not in event or 'instance_code' not in event:
        logger.error('[report event] error format')
        return None
    type_ = event['type']
    if type_ != 'approval_instance':
        return None

    approval_code = event.get('approval_code', None)
    if approval_code is None:
        return None
    # 1. 判断是否CS的审批
    if approval_code in APPROVALS_CS:
        bu_cs.tackle_event(event)

    # 生产kafka消息
    if raw is not None:
        if 'token' in raw:
            del raw['token']
    try:
        kafka_api.produce_json(kafka_api.TOPIC_APPROVAL_EVENT, raw, key=raw.get('uuid', None))
    except:
        logger.error('[approval event kafka] error: {}'.format(traceback.format_exc()))

