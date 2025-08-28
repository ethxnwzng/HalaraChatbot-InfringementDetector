import json
import traceback

import requests
from home.lark_client import bot
from home.config import constant
from util import http_util
from util.lark_util import Lark
from util.log_util import logger

REQUEST_SUCCESS = 200    # 请求成功
LINK_FORMAT_ERROR = 400  # 参数链接有问题
NO_PARAM_PROVIDED = 401  # 没有传入参数
REQUEST_FAILED = 500     # 请求失败 解析失败  -- cookie失效 接口失效




def parse_video_by_link(link, userinfo, retry_max=2):
    url = 'https://your-domain.com'
    retry = 0
    try:
        while retry < retry_max:
            retry += 1
            data = {'url': link}
            resp = requests.post(url=url, headers=http_util.get_json_headers(), data=json.dumps(data))
            if resp and resp.ok:
                resp = resp.json()
                code = resp['code']
                if code == 200:
                    return True, resp.get('data', None)
                else:
                    lark_info = {}
                    lark_info['nickname'] = userinfo.get('nickname',  '')
                    lark_info['name'] = userinfo.get('name', '')
                    lark_info['open_id'] = userinfo.get('open_id', '')
                    lark_info['fetch_link'] = link
                    lark_info['resp'] = resp
                    Lark(constant.LARK_CHAT_ID_P0).send_rich_text('idea_bot fetch error！！', json.dumps(lark_info))
                    return False, resp.get('msg', '无法解析该视频，请联系产研')
    except:
        logger.error('[parse video by link] error: {}'.format(traceback.format_exc()))
        Lark(constant.LARK_CHAT_ID_P0).send_rich_text('parse video by link error', traceback.format_exc())

    return False, 'request parse video error'

