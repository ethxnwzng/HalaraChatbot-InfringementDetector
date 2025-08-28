import json

import requests
from pytz import timezone
from django.db import connection
from home import meta, approval, dao
from home.enums import ApprovalStatus
from home.models import LarkApprovalInstance
from lark.settings import IS_PROD
from util import time_util, redis_util
from util.lark_util import Lark
from util.log_util import logger

APPROVAL_RETURN = 1
APPROVAL_REFUND = 2
APPROVAL_DISCOUNT = 3


cs_url = 'https://your-domain.com'
if IS_PROD:
    cs_url = 'https://your-domain.com'


def tackle_event(event):
    operate_time = event['operate_time']
    operate_time = time_util.get_cnt_from_timestamp(int(int(operate_time) / 1000))
    operate_time = operate_time.astimezone(timezone(time_util.TIMEZONE_BJ))
    status_raw = event['status']
    status = meta.MAP_APPROVAL_STATUS.get(status_raw, ApprovalStatus.UNKNOWN)
    status_display = meta.MAP_APPROVAL_STATUS_DISPLAY.get(status, 'Unknown')
    approval_result = None
    if status == ApprovalStatus.REJECTED:
        approval_result = 0
    elif status == ApprovalStatus.APPROVED:
        approval_result = 1
    elif status == ApprovalStatus.CANCELED:
        approval_result = 2

    instance_code = event['instance_code']
    instance_info = approval.get_approval_instance(instance_code)
    if instance_info is None or 'code' not in instance_info or instance_info['code'] != 0 or \
            'data' not in instance_info or instance_info['data'] is None:
        return None
    instance_info = instance_info['data']
    approval_code = instance_info['approval_code']
    approval_name = instance_info['approval_name']
    form = json.loads(instance_info['form'])
    open_id = instance_info['open_id']
    order_code = ''
    ticket_id = 0
    source = ''
    if form is not None and len(form) > 0:
        for item in form:
            if item['custom_id'] == 'order_code':
                order_code = item['value']
            if item['custom_id'] == 'ticket_id':
                ticket_id = int(item['value'])
            if item['custom_id'] == 'source':
                source = item['value']
    # get reject reason
    reason = ''
    timeline = instance_info['timeline']
    if timeline is not None and len(timeline) > 0:
        for item in timeline:
            if 'type' not in item or 'comment' not in item:
                continue
            if item['type'] == 'REJECT' or item['type'] == 'PASS':
                reason = item['comment']

    lark_content = '[Name] %s\n[Order] %s\n[Status] %s\n[Time] %s' \
                   % (approval_name, order_code, status_display, operate_time)

    # Lark(lark_url).send_rich_text('CS Approval Progress', lark_content)

    if approval_result is not None:
        notify(approval_code, ticket_id, approval_result, reason, order_code, source)

    # update db status
    if status != ApprovalStatus.PENDING:
        dao.mod_approval(instance_code=instance_code, approval_status=status)


def submit_approval(type_, data):
    type_ = int(type_)
    if data is None or len(data) == 0:
        return False, 'empty data'

    # 1. pickup type
    refund_key, refund_value, refund_widget_type = 'refund_num', float(data['refund']), 'number'
    if type_ == APPROVAL_RETURN:
        approval_code = meta.APPROVAL_CODE_RETURN
    elif type_ == APPROVAL_REFUND:
        approval_code = meta.APPROVAL_CODE_REFUND
    elif type_ == APPROVAL_DISCOUNT:
        approval_code = meta.APPROVAL_CODE_DISCOUNT
    else:
        return False, 'un-support type'

    # 2. construct form
    sku_list = data['sku_list']
    sku_list_form = []
    for sku in sku_list:
        sku_list_form.append([
            {'id': 'sku_code', 'type': 'input', 'value': sku['sku_code']},
            {'id': 'title', 'type': 'input', 'value': sku['title']},
            {'id': 'pay', 'type': 'input', 'value': sku['pay']},
            {'id': 'quantity', 'type': 'number', 'value': sku['quantity']},
            {'id': 'reason', 'type': 'input', 'value': sku['reason']},
        ])
    form = [
        {'id': 'order_code', 'type': 'input', 'value': str(data['order_code'])},
        {'id': 'ticket_id', 'type': 'input', 'value': str(data['ticket_id'])},
        {'id': 'order_reason', 'type': 'input', 'value': data['order_reason']},
        {'id': refund_key, 'type': refund_widget_type, 'value': refund_value},
        {'id': 'sku_list', 'type': 'fieldList', 'value': sku_list_form},
        {'id': 'ship_fee', 'type': 'input', 'value': data['ship_fee']},
        {'id': 'display_id', 'type': 'input', 'value': str(data['display_id'])},
        {'id': 'total_pay', 'type': 'input', 'value': data['total_pay']},
        {'id': 'order_name', 'type': 'input', 'value': data['order_name']},
        {'id': 'ship_status', 'type': 'input', 'value': data['ship_status']},
        {'id': 'tag', 'type': 'input', 'value': data['tag']},
        {'id': 'source', 'type': 'input', 'value': data['source']},
        {'id': 'reminders', 'type': 'input', 'value': data['reminders']},
        {'id': 'order_time', 'type': 'input', 'value': data['order_time']},
        {'id': 'deliver_time', 'type': 'input', 'value': data['deliver_time']},
        {'id': 'history_refund', 'type': 'input', 'value': data['history_refund']},
        {'id': 'op', 'type': 'input', 'value': data['op']},
        {'id': 'apply_type', 'type': 'number', 'value': data['apply_type']},
    ]

    received_sku_list = data['received_sku_list']
    if type_ == APPROVAL_REFUND and len(received_sku_list) > 0:
        received_sku_list_form = []
        for sku in received_sku_list:
            received_sku_list_form.append([
                {'id': 'received_sku_code', 'type': 'input', 'value': sku['sku_code']},
                {'id': 'received_quantity', 'type': 'number', 'value': sku['quantity']},
            ])
        form.append({'id': 'received_sku_list', 'type': 'fieldList', 'value': received_sku_list_form})

    # cs discount
    discount_info = data['discount_info']
    if type_ == APPROVAL_DISCOUNT and len(discount_info) > 0:
        form.append({'id': 'discount_type', 'type': 'input', 'value': discount_info['type']})
        form.append({'id': 'discount_history', 'type': 'input', 'value': discount_info['history']})
        form.append({'id': 'discount_amount', 'type': 'input', 'value': discount_info['amount']})

    # 3. submit
    user_id = data.get('user_id', None)
    detail = {'order_code': str(data['order_code']), 'ticket_id': str(data['ticket_id'])}
    return approval.create_approval(approval_code, form, detail=detail, user_id=user_id)


def notify(approval_code, ticket_id, approval_result, reason, order_id, source):
    if approval_code == meta.APPROVAL_CODE_RETURN:
        type_ = 1
    elif approval_code == meta.APPROVAL_CODE_REFUND:
        type_ = 2
    elif approval_code == meta.APPROVAL_CODE_DISCOUNT:
        type_ = 3
    else:
        return None

    headers = {'Content-Type': 'application/json', 'system-source': 'WEB'}
    data = {
        'ticketId': int(ticket_id),
        'result': int(approval_result),
        'reason': reason,
        'type': type_,
        'orderNo': int(order_id),
        'source': source
    }
    logger.info('[cs request] notify, %s' % data)
    resp = requests.post(cs_url, headers=headers, data=json.dumps(data))
    if resp is None or not resp.ok:
        logger.error('[cs request] failed to notify, %s' % resp)

    return None


def check_approval(instance_code):
    logger.info('[check approval] instance: %s' % instance_code)
    if instance_code is not None:
        instance = approval.get_approval_instance(instance_code)
        if instance is not None and 'code' in instance and instance['code'] == 0 and 'data' in instance:
            instance = instance['data']
            if 'status' in instance:
                status_raw = instance['status']
                status = meta.MAP_APPROVAL_STATUS.get(status_raw, ApprovalStatus.UNKNOWN)
                dao.mod_approval(instance_code, status)
                approval_result = None
                if status == ApprovalStatus.APPROVED:
                    approval_result = 1
                elif status == ApprovalStatus.REJECTED:
                    approval_result = 0
                elif status == ApprovalStatus.CANCELED:
                    approval_result = 2

                if approval_result is not None:
                    # get ticket_id
                    form = json.loads(instance['form'])
                    ticket_id = 0
                    order_code = ''
                    source = ''
                    if form is not None and len(form) > 0:
                        for item in form:
                            if item['custom_id'] == 'ticket_id':
                                ticket_id = int(item['value'])
                            if item['custom_id'] == 'order_code':
                                order_code = item['value']
                            if item['custom_id'] == 'source':
                                source = item['value']
                    # get detail
                    reason = ''
                    operate_time = ''
                    timeline = instance['timeline']
                    approval_name = instance['approval_name']
                    if timeline is not None and len(timeline) > 0:
                        for item in timeline:
                            if 'type' not in item:
                                continue
                            type_ = item['type']
                            if type_ == 'REJECT' or type_ == 'PASS' or type_ == 'CANCEL':
                                operate_time = time_util.get_cnt_from_timestamp(int(int(item['create_time']) / 1000))
                                operate_time = operate_time.astimezone(timezone(time_util.TIMEZONE_BJ))
                                if 'comment' in item:
                                    reason = item['comment']

                    notify(instance['approval_code'], ticket_id, approval_result, reason, order_code, source)
                    # lark
                    lark_content = '[Name] %s\n[Order] %s\n[Status] %s\n[Time] %s' \
                                   % (approval_name, order_code, meta.MAP_APPROVAL_STATUS_DISPLAY.get(status, 'Unknown'), operate_time)

                    Lark(approval.lark_url).send_rich_text('CS Approval Progress(Manual Check)', lark_content)


def cron_check_approval():
    key = 'lock:check-approval'
    if not redis_util.set_nx(key):
        return
    logger.info('[check approval] begin')
    count = 0
    instances = LarkApprovalInstance.objects.filter(approval_status=ApprovalStatus.PENDING.value, deleted=0)
    if instances is not None and len(instances) > 0:
        for ins in instances:
            count += 1
            check_approval(ins.instance_code)
    logger.info('[check approval] end, count: %s' % count)
    connection.close()

