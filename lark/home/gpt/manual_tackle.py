import json
import os

import django
import requests
os.environ['DJANGO_SETTINGS_MODULE'] = 'lark.settings'
django.setup()

from home.gpt.dto import WORK_SYMBOL, JSON_KEY_EXCEL_DATA, JSON_KEY_EXCEL_NAME
from home.models import LarkUserWorkbench
from util import http_util

from home.config import constant
from home.gpt import review, script, dto
from home.gpt.review_reader import warehouse, self_tag, meta
from home.idea_bot import client as bot_client


def manual_merge():
    req_merge = review.RequestMergeReview()
    req_merge.user_id = constant.LARK_USER_ID_LUKE
    req_merge.replies = warehouse.replies
    merge_prompt = review.DEFAULT_MERGE_PROMPT.replace('#object_desc#', review.DEFAULT_OBJ_DESC).replace('#extra_desc#', review.PROMPT_CONS)
    req_merge.merge_prompt = merge_prompt
    req_merge.system_prompt = ''
    req_merge.temperature = 0.0
    req_merge.use_lark = True
    o = review.merge_replies_by_chatgpt(req_merge)
    print(o)


def manual_trim(reply):
    point_list = script.parse_analyze(reply)
    record = LarkUserWorkbench.objects.filter(lark_user_id=constant.LARK_USER_ID_LUKE, work_symbol=WORK_SYMBOL).first()
    if not record:
        bot_client.send_text_with_title('user_id', constant.LARK_USER_ID_LUKE, 'no record of {}'.format(WORK_SYMBOL), constant.LARK_USER_ID_LUKE)
        return

    excel_data = record.detail.get(JSON_KEY_EXCEL_DATA, [])
    excel_name = record.detail.get(JSON_KEY_EXCEL_NAME, '')
    map_reviews = dto.get_db_map_reviews(excel_data)
    point_list, out_ids = self_tag.check_report(point_list, map_reviews, meta.CHECK_TOP_COUNT, auto_trim=True)
    title = 'Reviews Report Trimmed: {}'.format(excel_name)
    trim_reply = ''
    for each in point_list:
        trim_reply += '- {} ({})\n'.format(each['point'], ', '.join(each['ids']))
    bot_client.send_text_with_title('user_id', constant.LARK_USER_ID_LUKE, title, trim_reply)


def manual_trim_http(dimension='cons'):
    data = {'reply': warehouse.analyze[dimension]}
    url = 'https://your-domain.com'
    resp = requests.post(url, headers=http_util.get_json_headers(), data=json.dumps(data))
    print(resp.text)


if __name__ == '__main__':
    manual_trim_http(dimension='scenario')

