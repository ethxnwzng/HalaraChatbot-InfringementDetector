"""
NOTE: This file has been sanitized for portfolio display.
Replace placeholder values with actual credentials for production use.
"""

import json
import requests
from util.log_util import logger


APP_ID = "your_app_id_here"
APP_SECRET = "your_app_secret_here"
CHAT_BOT_NAME = 'idea_bot'

# Test environment settings
TEST_CHAT_ID = os.getenv('TEST_CHAT_ID', 'your_test_chat_id_here')  # Chat ID for testing


def get_token():
    """Get a tenant access token for the idea bot using its credentials"""
    url = 'https://your-feishu-instance.com'
    headers = {'Content-Type': 'application/json; charset=utf-8'}
    data = {'app_id': APP_ID, 'app_secret': APP_SECRET}
    logger.info(f'[idea_bot token] Attempting to get token with app_id: {APP_ID}')
    
    try:
        resp = requests.post(url=url, headers=headers, data=json.dumps(data))
        logger.info(f'[idea_bot token] Response status: {resp.status_code}, body: {resp.text}')
        if resp.ok:
            resp = json.loads(resp.text)
            if resp['code'] == 0:
                return resp['tenant_access_token']
            logger.error(f'[idea_bot token] failed to get token: {resp}')
    except Exception as e:
        logger.error(f'[idea_bot token] Exception: {str(e)}')
    return None


def get_headers(content_type='application/json'):
    """Get headers specifically for the idea bot using its credentials"""
    token = get_token()
    if token is None:
        return None
    headers = {'Authorization': f'Bearer {token}'}
    if content_type:
        headers['Content-Type'] = f'{content_type}; charset=utf-8'
    return headers


if __name__ == '__main__':
    o = get_headers()
    print(o)
