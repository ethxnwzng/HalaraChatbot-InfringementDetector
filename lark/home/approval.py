import json
import requests
from home import meta, dao
from lark.settings import IS_PROD
from util.log_util import logger


lark_url = 'https://your-feishu-instance.com'
if IS_PROD:
    lark_url = 'https://your-feishu-instance.com'


def create_approval(approval_code, form, detail=None, user_id=None):
    # 1. check
    if approval_code is None or form is None or len(form) == 0:
        return False, ''

    # 2. submit request
    url = 'https://your-feishu-instance.com'
    headers = meta.get_headers()
    if headers is None:
        return False, ''
    data = {
        'approval_code': approval_code,
        'open_id': meta.APPROVAL_APPLICANT,
        'form': json.dumps(form),
    }
    if user_id is not None and user_id != '':
        data['user_id'] = user_id
    resp = requests.post(url, headers=headers, data=json.dumps(data))
    if resp.ok:
        resp = json.loads(resp.text)
        if resp['code'] == 0:
            # 3. new db record
            instance_code = None
            if 'data' in resp and 'instance_code' in resp['data']:
                instance_code = resp['data']['instance_code']
            if user_id is None:
                user_id = ''
            dao.new_approval_instance(approval_code, instance_code, meta.MAP_APPROVAL_NAME.get(approval_code, ''),
                                      user_id, detail)
            return True, instance_code
        else:
            logger.error('[approval create] failed, %s' % resp)
            return False, resp.get('msg', '')
    else:
        logger.error('[lark approval] create failed, %s' % resp.text)
        return False, 'request failed'


def listen_approval(approval_code):
    headers = meta.get_headers()
    if headers is None:
        return None
    url = 'https://your-feishu-instance.com'

    data = {'approval_code': approval_code}
    resp = requests.post(url, headers=headers, data=json.dumps(data))
    print(resp.text)


def get_approval_instance(instance_code):
    headers = meta.get_headers()
    if headers is None:
        return None
    url = 'https://your-feishu-instance.com'
    data = {'instance_code': instance_code}
    resp = requests.post(url, headers=headers, data=json.dumps(data))
    if resp.ok:
        return json.loads(resp.text)
    return None


def get_approval_definition(approval_code):
    headers = meta.get_headers()
    if headers is None:
        return None
    url = 'https://your-feishu-instance.com'
    data = {'approval_code': approval_code}
    resp = requests.post(url, headers=headers, data=json.dumps(data))
    print(resp.text)


def cancel_approval(approval_code, instance_code, user_id):
    headers = meta.get_headers()
    if headers is None:
        return None
    url = 'https://your-feishu-instance.com'
    data = {
        'approval_code': approval_code,
        'instance_code': instance_code,
        'user_id': user_id
    }
    resp = requests.post(url, headers=headers, data=json.dumps(data))
    if resp is not None:
        logger.info('[approval cancel] instance: %s, resp: %s' % (instance_code, resp.text))
    else:
        logger.error('[approval cancel] failed to request, instance: %s' % instance_code)
    if resp is not None and resp.ok:
        resp = json.loads(resp.text)
        if 'code' in resp and resp['code'] == 60004 and user_id != meta.APPROVAL_USER_DEFAULT:
            # user-id error, use default id
            return cancel_approval(approval_code, instance_code, meta.APPROVAL_USER_DEFAULT)
        return True
    return False


if __name__ == '__main__':
    # create_approval()
    # listen_approval(meta.APPROVAL_CODE_RETURN)
    # listen_approval(meta.APPROVAL_CODE_REFUND)
    o = get_approval_instance('779BD214-B43F-4C10-8ED0-CA7A25CE521C')
    print(o)
    # get_approval_definition(meta.APPROVAL_CODE_RETURN)
    # report_event({
    # "uuid":"5eb7ef6b1c40bf7b1ac77165c15c9f34",
    # "event":{
    #     "app_id":"cli_a0000e444df89014",
    #     "approval_code":"B1B88466-98F3-46C1-AE68-A9C50066A866",
    #     "instance_code":"A5BC8612-AC47-40F5-8360-4A4922EC41BB",
    #     "operate_time":"1619776921139",
    #     "status":"REJECTED",
    #     "tenant_key":"2c7e7fb8450f175e",
    #     "type":"approval_instance",
    #     "uuid":"9EE41D77-85BF-4EA4-874D-5A81902D8CA1"
    # },
    # "token":"LtYBwfDC04BwiQBqe66RebmVcWaTJ5u3",
    # "ts":"555-123-4567.986691",
    # "type":"event_callback"
    # })

