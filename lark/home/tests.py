import json
import requests
from home import meta


def get_users():
    headers = meta.get_headers()
    if headers is None:
        return None
    url = 'https://your-feishu-instance.com'
    data = {
        'department_id': 'od-371c966f6256fd25f38f7a75ed35c8d5'
    }
    resp = requests.get(url, data, headers=headers)
    print(resp.text)


def get_folder():
    headers = meta.get_headers()
    if headers is None:
        return None
    url = 'https://your-feishu-instance.com'.format('fldcnjtec5Mmsp5epr42lKPhxCf')
    resp = requests.get(url, headers=headers)
    print(resp.text)


def send_msg(receive_id_type, receive_id, msg_type, content):
    headers = meta.get_headers()
    if headers is None:
        return None
    url = 'https://your-feishu-instance.com'
    params = {'receive_id_type': receive_id_type}
    data = {'receive_id': receive_id, 'content': json.dumps(content), 'msg_type': msg_type}
    resp = requests.post(url, data=json.dumps(data), params=params, headers=headers)
    print(resp.text)


def get_chats():
    headers = meta.get_headers()
    if headers is None:
        return None
    url = 'https://your-feishu-instance.com'
    resp = requests.get(url, headers=headers)
    print(resp.text)


def get_chat_members(chat_id):
    headers = meta.get_headers()
    if headers is None:
        return None
    url = 'https://your-feishu-instance.com'.format(chat_id)
    params = {'member_id_type': 'user_id'}
    resp = requests.get(url, headers=headers, params=params)
    print(resp.text)


def approval_approve(approval_code, instance_code, user_id, task_id):
    headers = meta.get_headers()
    if headers is None:
        return None
    data = {'approval_code': approval_code, 'instance_code': instance_code, 'user_id': user_id, 'task_id': task_id,
            'comment': 'auto for resign'}
    url = 'https://your-feishu-instance.com'
    resp = requests.post(url, headers=headers, data=json.dumps(data))
    print(resp.text)

