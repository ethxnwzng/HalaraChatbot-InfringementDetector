import json
import traceback

import requests

from home.config import constant
from home.lark_client import meta
from util.lark_util import Lark
from util.log_util import logger


RECEIVE_ID_TYPE_CHAT = 'chat_id'
RECEIVE_ID_TYPE_USER = 'user_id'


def send_msg(receive_id_type, receive_id, msg_type, content, retry_max=2, headers=None):
    if not headers:
        headers = meta.get_headers()
    if headers is None:
        return None
    url = 'https://your-feishu-instance.com'
    params = {'receive_id_type': receive_id_type}
    data = {'receive_id': receive_id, 'content': json.dumps(content), 'msg_type': msg_type}
    retry = 0
    while retry < retry_max:
        retry += 1
        try:
            resp = requests.post(url, data=json.dumps(data), params=params, headers=headers)
            if resp and resp.ok:
                return resp.json()
            else:
                logger.error('[send] error: {}, retry: {}'.format(resp.text, retry))
        except:
            logger.error('[lark send msg exception]: {}'.format(traceback.format_exc()))
            Lark(constant.LARK_CHAT_ID_P0).send_rich_text('lark send msg exception', traceback.format_exc())
    return None


def send_txt(receive_id_type, receive_id, text, headers=None):
    content = {'text': text}
    send_msg(receive_id_type, receive_id, 'text', content, headers=headers)


def send_text_with_title(receive_id_type, receive_id, title, text, at=None, headers=None):
    content = {
        "zh_cn": {
            "title": title,
            "content": [
                [{
                    "tag": "text",
                    "text": text
                }]
            ]
        }
    }
    # at指定人
    if at:
        ats = at
        content_at = []
        if type(at) == str:
            ats = [at]
        for each in ats:
            if each:
                content_at.append({'tag': 'at', 'user_id': each})
        content['zh_cn']['content'].append(content_at)

    send_msg(receive_id_type, receive_id, 'post', content, headers=headers)


def get_chats():
    headers = meta.get_headers()
    if headers is None:
        return None
    url = 'https://your-feishu-instance.com'
    max_page = 100
    page = 0
    page_size = 100
    has_more, page_token, count = False, None, 0
    while page < max_page:
        page += 1
        params = {'page_token': page_token, 'page_size': page_size}
        resp = requests.get(url, headers=headers, params=params)
        if resp.ok:
            data = resp.json()['data']
            has_more = data['has_more']
            page_token = data['page_token']
            items = data['items']
            for item in items:
                count += 1
                print('{}. {}: {}'.format(count, item['name'], item['chat_id']))
            if not has_more:
                break


def get_chat_members(chat_id):
    result, user_ids = [], []
    headers = meta.get_headers()
    if headers is None:
        return None, None
    url = 'https://your-feishu-instance.com'.format(chat_id)
    max_page = 100
    page = 0
    page_size = 100
    has_more, page_token, count = False, None, 0
    while page < max_page:
        page += 1
        params = {'page_token': page_token, 'page_size': page_size, 'member_id_type': 'user_id'}
        resp = requests.get(url, headers=headers, params=params)
        if resp.ok:
            data = resp.json()['data']
            has_more = data['has_more']
            page_token = data['page_token']
            items = data['items']
            for item in items:
                result.append({'name': item['name'], 'user_id': item['member_id']})
                user_ids.append(item['member_id'])
            if not has_more:
                break
    return result, user_ids


def get_user(user_id, user_id_type='user_id'):
    headers = meta.get_headers()
    if headers is None:
        return None
    url = 'https://your-feishu-instance.com' + user_id
    data = {
        'user_id_type': user_id_type
    }
    resp = requests.get(url, data, headers=headers)
    if resp and resp.json():
        return resp.json().get('data', {})


def get_department(department_id):
    headers = meta.get_headers()
    if headers is None:
        return None
    url = 'https://your-feishu-instance.com' + department_id
    resp = requests.get(url, headers=headers)
    if resp and resp.json():
        return resp.json().get('data', {})


def get_department_name_path(department_id):
    department_info = get_department(department_id)['department']
    name = department_info['name']
    loop_max = 10
    loop = 0
    while loop < loop_max:
        if parent_department_id := department_info.get('parent_department_id', None):
            if parent_department_id == '0':
                break
            parent_department = get_department(parent_department_id)['department']
            name += '/{}'.format(parent_department['name'])
            department_info = parent_department
        else:
            break
    return name


def get_file(file_key: str) -> dict:
    """Download a file from Lark using its file_key"""
    try:
        headers = meta.get_headers()
        if headers is None:
            logger.error('Failed to get headers for file download')
            return None
            
        # Get file content directly
        download_url = f'https://your-feishu-instance.com'
        logger.info(f'Downloading file with key: {file_key}')
        logger.info(f'Using URL: {download_url}')
        logger.info(f'Headers: {headers}')
        
        response = requests.get(download_url, headers=headers, stream=True)
        
        if not response.ok:
            logger.error(f'Failed to download file. Status code: {response.status_code}')
            logger.error(f'Response text: {response.text}')
            return None
            
        # Get filename from Content-Disposition header if available
        content_disposition = response.headers.get('Content-Disposition', '')
        filename = 'downloaded_file'
        if 'filename=' in content_disposition:
            filename = content_disposition.split('filename=')[1].strip('"')
        elif 'filename*=' in content_disposition:
            filename = content_disposition.split('filename*=')[1].split("'")[-1]
        
        # Get content type from Content-Type header
        content_type = response.headers.get('Content-Type', '')
        
        # Read the entire response content
        content = response.content
        
        logger.info(f'Successfully downloaded file: {filename} ({content_type})')
        logger.info(f'Content size: {len(content)} bytes')
        
        return {
            'content': content,
            'name': filename,
            'type': content_type
        }
        
    except Exception as e:
        logger.error(f'Error downloading file: {str(e)}')
        logger.error(f'Traceback: {traceback.format_exc()}')
        return None


if __name__ == '__main__':
    # send_txt('user_id', constant.LARK_USER_ID_LUKE, 'hi')
    get_chats()
    # o = get_chat_members('oc_eaf81600be37424fdf033ba9a7e33a4c')
    # print(len(o), o)
    # o = get_user('cfg1cge2')
    # o = get_department_name_path('od-dca5db11841fd7bc80d3648846f23607')
    # print(json.dumps(o))
    # print(o) 