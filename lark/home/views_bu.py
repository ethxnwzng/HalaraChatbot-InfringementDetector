import json
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from home import bu_cs
from util import http_util
from util.log_util import logger


@csrf_exempt
def cs_submit_approval(request):
    if request is None or request.body is None:
        return http_util.wrap_err_response(-1, 'empty post json body')
    data = json.loads(request.body)
    logger.info('[approval request] /approval/cs/submit, data: %s' % data)
    # 1. parse data
    ticket_id = data.get('ticketId', None)
    display_id = data.get('displayId', None)
    type_ = data.get('type', None)
    op_id = data.get('opId', None)
    op = data.get('op', '')
    tag = data.get('tag', '')
    source = data.get('source', '未知')
    order = data.get('order', None)
    apply_type = int(data.get('applyType', 0))
    if ticket_id is None or type_ is None or order is None:
        return http_util.wrap_err_response(-1, 'empty ticketId, type or order')
    order_code = order.get('orderNo', None)
    order_reason = order.get('reason', '')
    items = order.get('items', None)
    if order_code is None or items is None:
        return http_util.wrap_err_response(-1, 'empty orderNo or items')
    sku_list = []
    for item in items:
        sku_code = item.get('skuCode', None)
        title = item.get('title', '')
        pay = item.get('totalPayment', None)
        quantity = item.get('quantity', 0)
        reason = item.get('reason', '')
        if sku_code is None:
            continue
        sku_list.append({'sku_code': sku_code, 'title': title, 'pay': pay, 'quantity': quantity, 'reason': reason})
    refund = order.get('applyAmount', None)
    if refund is None:
        return http_util.wrap_err_response(-1, 'empty applyAmount')

    received_sku_list = []
    if type_ == bu_cs.APPROVAL_REFUND and 'returnedItems' in order:
        received_items = order['returnedItems']
        if received_items is not None and len(received_items) > 0:
            for received_item in received_items:
                sku_code = received_item.get('skuCode', None)
                quantity = received_item.get('quantity', 0)
                if sku_code is None:
                    continue
                received_sku_list.append({'sku_code': sku_code, 'quantity': quantity})

    ship_fee = order.get('shippingAmount', '')
    total_pay = order.get('totalPayment', '')
    order_name = order.get('orderName', '')
    ship_status = order.get('shipStatus', '')
    reminders = order.get('reminders', '')
    order_time = order.get('orderTime', '')
    deliver_time = order.get('deliveredDate', '')
    history_refund = order.get('historyRefundAmount', '')

    # CS优惠
    discount_info = {}
    discount = data.get('discount', None)
    if type_ == bu_cs.APPROVAL_DISCOUNT and discount is not None:
        discount_info['type'] = discount.get('type', '')
        discount_info['amount'] = discount.get('amount', '')
        discount_info['history'] = discount.get('history', '')

    # 2. submit struct
    submit = {'order_code': order_code, 'order_reason': order_reason, 'sku_list': sku_list, 'refund': refund,
              'ticket_id': ticket_id, 'received_sku_list': received_sku_list, 'ship_fee': ship_fee,
              'display_id': display_id, 'total_pay': total_pay, 'order_name': order_name, 'user_id': op_id,
              'ship_status': ship_status, 'tag': tag, 'source': source, 'reminders': reminders, 'order_time': order_time,
              'deliver_time': deliver_time, 'history_refund': history_refund, 'discount_info': discount_info, 'op': op,
              'apply_type': apply_type}
    ok, tips = bu_cs.submit_approval(type_, submit)
    if not ok:
        return http_util.wrap_err_response(-1, tips)

    return http_util.wrap_ok_response({'approvalId': tips})
