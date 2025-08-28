import json
import traceback

import requests

from home.config import constant
from util.lark_util import Lark
from util.log_util import logger

APPROVAL_ID = 'cli_a0000e444df89014'
APPROVAL_SECRET = os.getenv('APPROVAL_SECRET', 'your_approval_secret_here')
APPROVAL_APPLICANT = os.getenv('APPROVAL_APPLICANT', 'your_approval_applicant_here')


def get_token(app_id=None, app_secret=None, retry_max=2):
    if not app_id or not app_secret:
        app_id = APPROVAL_ID
        app_secret = APPROVAL_SECRET
    url = 'https://your-feishu-instance.com'
    headers = {'Content-Type': 'application/json; charset=utf-8'}
    data = {'app_id': app_id, 'app_secret': app_secret}
    logger.info(f'[lark token] Attempting to get token with app_id: {app_id}')
    retry = 0
    while retry < retry_max:
        retry += 1
        try:
            resp = requests.post(url=url, headers=headers, data=json.dumps(data))
            logger.info(f'[lark token] Response status: {resp.status_code}, body: {resp.text}')
            if resp.ok:
                resp = json.loads(resp.text)
                if resp['code'] == 0:
                    return resp['tenant_access_token']
                logger.error(f'[lark token] failed to get token: {resp}')
        except Exception as e:
            logger.error('[lark token exception] {}'.format(traceback.format_exc()))
            Lark(constant.LARK_CHAT_ID_P0).send_rich_text('lark token exception', traceback.format_exc())
    return None


def get_headers(app_id=None, app_secret=None, content_type='application/json'):
    """Get headers for Lark API requests.
    
    Args:
        app_id: Optional app ID. If not provided, uses default.
        app_secret: Optional app secret. If not provided, uses default.
        content_type: Content type for the request. Defaults to 'application/json'.
                     For file uploads, should be None to let requests set it.
    
    Returns:
        dict: Headers including Authorization and optionally Content-Type
    """
    token = get_token(app_id=app_id, app_secret=app_secret)
    if token is None:
        logger.error('failed to get token')
        return None
        
    headers = {'Authorization': f'Bearer {token}'}
    if content_type:
        headers['Content-Type'] = f'{content_type}; charset=utf-8'
    return headers


