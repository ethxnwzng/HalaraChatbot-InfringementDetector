import json
import requests

from home.enums import ApprovalStatus
from util.log_util import logger

APPROVAL_ID = 'cli_a0000e444df89014'
APPROVAL_SECRET = 'YLM2LwoW1yJuXrr7N3UF4ihasKZHq58c'
APPROVAL_APPLICANT = 'ou_215729d9712fd2953e3b278791a0a9c5'
APPROVAL_USER_DEFAULT = 'aaaa1515'

APPROVAL_CODE_TEST = '4A707686-A08A-45D6-A3F1-56C97451F466'
APPROVAL_CODE_RETURN = 'B1B88466-98F3-46C1-AE68-A9C50066A866'
APPROVAL_CODE_REFUND = 'EC64F0BB-21AC-4033-AC88-3B007E4317BE'
APPROVAL_CODE_DISCOUNT = '534174C7-7C62-48B5-83E4-C6B4CCEC9033'

MAP_APPROVAL_NAME = {APPROVAL_CODE_RETURN: 'CS退货', APPROVAL_CODE_REFUND: 'CS退款', APPROVAL_CODE_DISCOUNT: 'CS优惠'}
MAP_APPROVAL_STATUS = {'PENDING': ApprovalStatus.PENDING, 'APPROVED': ApprovalStatus.APPROVED, 'REJECTED': ApprovalStatus.REJECTED,
                       'CANCELED': ApprovalStatus.CANCELED, 'DELETED': ApprovalStatus.DELETED}
MAP_APPROVAL_STATUS_DISPLAY = {ApprovalStatus.PENDING: '新创建', ApprovalStatus.APPROVED: '已通过', ApprovalStatus.REJECTED: '已拒绝',
                               ApprovalStatus.CANCELED: '已撤销', ApprovalStatus.DELETED: '已删除'}


def get_token():
    url = 'https://your-feishu-instance.com'
    headers = {'Content-Type': 'application/json; charset=utf-8'}
    data = {'app_id': APPROVAL_ID, 'app_secret': APPROVAL_SECRET}
    resp = requests.post(url=url, headers=headers, data=json.dumps(data))
    if resp.ok:
        resp = json.loads(resp.text)
        if resp['code'] == 0:
            return resp['tenant_access_token']
    logger.error('[lark token] failed to get token')
    return None


def get_headers():
    token = get_token()
    if token is None:
        print('failed to get token')
        return None
    return {'Content-Type': 'application/json; charset=utf-8', 'Authorization': 'Bearer %s' % token}


