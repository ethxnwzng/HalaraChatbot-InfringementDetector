import json

import requests

from util import http_util
from util.log_util import logger

HOST = 'https://your-domain.com'


def detect_face(pic_url=None, ad_id=None, fb_url=None):
    url = f'{HOST}/api/face/detect'
    data = {'pic_url': pic_url, 'ad_id': ad_id, 'fb_url': fb_url}
    resp = requests.post(url, headers=http_util.get_json_headers(), data=json.dumps(data))
    logger.info('[review export lark]: {}'.format(resp.text))
    if resp and resp.ok:
        return resp.json()['data']
    return None


if __name__ == '__main__':
    url_ = 'https://dfs-crawler.s3.cn-northwest-1.amazonaws.com.cn/lark/upload/7358ce-b52a22c7-849f-4b88-b10c-d72d83a785aa.jpeg'
    o = detect_face(pic_url=url_)
