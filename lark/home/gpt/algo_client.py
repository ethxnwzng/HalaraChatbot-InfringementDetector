import json

import requests

from home.config import constant
from home.gpt import script
from home.gpt.review_reader import warehouse
from util import http_util
from util.lark_util import Lark
from util.log_util import logger


def merge_points(replies, retry_max=3):
    if not replies:
        return None
    map_point_weight, map_point_ids, result_points = {}, {}, []
    # 1. trim points
    for reply in replies:
        reply = str(reply).strip()
        points = script.parse_analyze(reply)
        for each in points:
            point = each['point']
            ids = each['ids']
            if point not in map_point_ids:
                map_point_ids[point] = ids
            else:
                map_point_ids[point] = list(set(map_point_ids[point] + ids))
    map_point_weight = {k: len(v) for (k, v) in map_point_ids.items()}
    # 2. request algo api
    url = 'http://192.168.1.1:8090/voc/merge'
    retry, map_summary_points = 0, {}
    while retry < retry_max:
        retry += 1
        resp = requests.post(url, headers=http_util.get_json_headers(), data=json.dumps(map_point_weight))
        logger.info('[chatgpt reviews algo merge] request: {}, response: {}'.format(json.dumps(map_point_weight), resp.text))
        if resp and resp.ok:
            resp = resp.json()
            if 'result' in resp:
                map_summary_points = resp['result']
                break
        if resp and not map_summary_points:
            logger.error('[chatgpt reviews request failed] call algo api failed, raw: {}, resp: {}'.format(map_point_weight, resp.text))
            Lark(constant.LARK_CHAT_ID_P0).send_rich_text('chatgpt reviews request failed', 'call algo api failed, raw: {}, resp: {}'.format(map_point_weight, resp.text))
    # 3. wrap result
    for new_point, old_points in map_summary_points.items():
        ids = []
        for old_point in old_points:
            ids = list(set(ids + map_point_ids.get(old_point, [])))
        ids.sort(key=lambda x: int(x))
        result_points.append({'point': new_point, 'ids': ids})

    result_points.sort(key=lambda x: len(x['ids']), reverse=True)
    return result_points


if __name__ == '__main__':
    merge_points(warehouse.replies)

