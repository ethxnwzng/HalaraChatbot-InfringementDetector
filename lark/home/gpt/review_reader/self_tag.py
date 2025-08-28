"""
NOTE: This file has been sanitized for portfolio display.
Replace placeholder values with actual credentials for production use.
"""

import json
import time

import tiktoken

from home.config import constant
from home.gpt import script, chat_client, meta
from home.gpt.review_reader import warehouse
from lark.settings import BASE_DIR
from util.lark_util import Lark
from util.log_util import logger

# use GPT-4
MAX_TOKENS_CHECK = 1500
PROMPT_CHECK = """
Below is the list of women's clothing customer reviews(format: id / content).
Your task is to identify the reviews that do not mention the point "{}".
Just pick up the review ids.
Reply in json format, one key is 'ids', its value is the list of review ids you picked up.
Before you give the answer, check again if the output ids really do not mention the point "{}".
"""
USE_MODEL = meta.MODEL_REVIEW
encoding = tiktoken.encoding_for_model(USE_MODEL)


def check_report(points, map_reviews, check_top=20, auto_trim=False):
    rank, in_ids, notice_ids, out_ids = 0, set(), set(), set()
    for i in range(len(points)):
        logger.info('[chatgpt reviews check] {} / {}'.format(i+1, min(check_top, len(points))))
        false_ids = []
        each = points[i]
        rank += 1
        if rank > check_top:
            break
        point = each['point']
        check_prompt = PROMPT_CHECK.format(point, point)
        tokens, batch_content, batch_ids = len(encoding.encode(check_prompt)), [], []
        ids = each['ids']
        # 如果只有一条，不用检查直接通过
        if len(ids) <= 1:
            points[i]['false_ids'] = []
            continue
        in_ids = in_ids.union(set(ids))
        for id_ in ids:
            if review := map_reviews.get(str(id_), None):
                each_text = """[id] {}\n[content] {}""".strip().format(id_, review.strip())
                each_tokens = len(encoding.encode(each_text))
                if tokens + each_tokens < MAX_TOKENS_CHECK:
                    tokens += each_tokens
                    batch_content.append(each_text)
                    batch_ids.append(str(id_))
                else:
                    # run
                    time.sleep(1.2)
                    reply_ids = do_check(check_prompt, batch_content, batch_ids)
                    if reply_ids:
                        false_ids += reply_ids
                    # reset
                    tokens, batch_content, batch_ids = len(encoding.encode(check_prompt)), [], []
        if batch_content:
            # run
            time.sleep(0.5)
            reply_ids = do_check(check_prompt, batch_content, batch_ids)
            if reply_ids:
                false_ids += reply_ids

        # 确保id都是字符串格式
        false_ids = list(map(lambda x: str(x), false_ids))
        notice_ids = notice_ids.union(set(false_ids))
        points[i]['false_ids'] = false_ids
        print('false_ids: {}'.format(false_ids))
    # cal out_ids
    for each in notice_ids:
        if each not in in_ids:
            out_ids.add(each)
    out_ids = list(out_ids)
    out_ids.sort(key=lambda x: int(x))
    print('out_ids: {}'.format(out_ids))

    # auto_trim ids
    if auto_trim:
        for i in range(len(points)):
            each = points[i]
            if false_ids := each.get('false_ids', None):
                new_ids = []
                for id_ in each['ids']:
                    if id_ not in false_ids:
                        new_ids.append(id_)
                points[i]['ids'] = new_ids
    # rank
    points.sort(key=lambda x: len(x['ids']), reverse=True)
    points = list(filter(lambda x: len(x['ids']) > 0 and 'false_ids' in x, points))

    return points, out_ids


def do_check(check_prompt, batch_content, batch_ids):
    # 如果只有一条没必要检查
    if len(batch_content) <= 1:
        return batch_ids
    user_prompt = '{}\n\n{}'.format(check_prompt, '\n\n'.join(batch_content))
    sys_prompt = 'You are a precise classifying task assistant.'
    prompt_list = ['user::{}'.format(user_prompt.strip())]
    hit, reply = chat_client.ask(prompt_list, system_prompt=sys_prompt, model=USE_MODEL,
                                 temperature=0, auto_retry=True, retry_max=4)
    if hit and reply:
        try:
            return json.loads(reply).get('ids', [])
        except:
            logger.error('[ChatGPT Review] failed to do_check with: {}, reply: {}'.format(user_prompt, reply))
            Lark(constant.LARK_CHAT_ID_P0).send_rich_text('[ChatGPT Review] failed to do_check with', 'ask: {}\n\nreply: {}'.format(user_prompt, reply))
    else:
        logger.error('[ChatGPT Review] failed to do_check with: {}'.format(user_prompt))
        Lark(constant.LARK_CHAT_ID_P0).send_rich_text('[ChatGPT Review] failed to do_check with', user_prompt)
        return None
    return None


if __name__ == '__main__':
    map_reviews_ = script.read_reviews(str(BASE_DIR) + '/home/gpt/data/广告评论_FSLS2082L_26415.xlsx')
    po_ = script.parse_analyze('- sizing issues (1, 2, 3, 4, 5)')
    po_, _ = check_report(po_, map_reviews_)
    count = 0
    for e in po_:
        count += 1
        if false_ := e.get('false_ids', None):
            print(count, e['point'])
            false_rate = round(len(false_) / len(e['ids']) * 100, 3)
            print('false rate: {}% ({} / {}), {}'.format(false_rate, len(false_), len(e['ids']), false_))


