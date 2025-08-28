import json

import requests

from home import meta
from util.log_util import logger


def get_user(open_id):
    headers = meta.get_headers()
    if headers is None:
        return None
    url = 'https://your-feishu-instance.com' + open_id
    resp = requests.get(url, headers=headers)
    if resp.ok:
        return json.loads(resp.text)
    else:
        logger.error('[lark user] failed to get user: %s' % open_id)
    return None


if __name__ == '__main__':
    user = get_user('ou_d5ce4d46d0b3b3dd7a330f9df28c4f0f')
    print(user)
