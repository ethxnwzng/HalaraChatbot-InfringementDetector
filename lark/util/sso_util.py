"""
NOTE: This file has been sanitized for portfolio display.
Replace placeholder values with actual credentials for production use.
"""

from urllib import parse
import requests
from home.config import constant


def get_sso_url(redirect_url):
    sso_url = 'https://your-feishu-instance.com'
    params = {'client_id': constant.LARK_APP_ID, 'redirect_uri': constant.SSO_CALLBACK, 'response_type': 'code', 'state': redirect_url}
    return sso_url + parse.urlencode(params)


def get_access_token(code):
    url = 'https://your-feishu-instance.com'
    params = {'grant_type': 'authorization_code', 'client_id': constant.LARK_APP_ID, 'client_secret': constant.LARK_APP_SECRET,
              'code': code, 'redirect_uri': constant.SSO_CALLBACK}
    resp = requests.post(url, params=params)
    hit = False
    token = ''
    if resp.ok:
        if 'access_token' in resp.json():
            hit = True
            token = resp.json()['access_token']
    elif 'error_description' in resp.json():
        token = resp.json()['error_description']
    return hit, token


def get_user_info(token):
    url = 'https://your-feishu-instance.com'
    headers = {'Authorization': 'Bearer {}'.format(token)}
    resp = requests.get(url, headers=headers)
    hit = False
    if resp.ok and 'name' in resp.json() and 'user_id' in resp.json():
        hit = True
    data = resp.json()
    return hit, data


if __name__ == '__main__':
    token_ = '2sbmPeGYd8cFvM2HpZl0315l1Jhlhk6bNE00g5Q02zGM'
    h, o = get_user_info(token_)
    print(h, o)
