import json

import requests

from util.log_util import logger


def listen_task(event_data):
    headers = {'Content-Type': 'application/json; charset=utf-8'}
    logger.info('[Lark Notify] task_data: {}'.format(event_data))
    test_url = 'https://your-domain.com'
    prod_url = 'https://your-domain.com'
    resp = requests.post(prod_url, headers=headers, data=json.dumps(event_data))
    print(resp.text)
    logger.info('[Lark Notify] resp: {}'.format(resp.text))


if __name__ == '__main__':
    listen_task({'schema': '2.0', 'header': {'event_id': '7f752a21d793a9f571372dd1ff9655a6', 'token': 'LtYBwfDC04BwiQBqe66RebmVcWaTJ5u3', 'create_time': '1642660636000', 'event_type': 'task.task.updated_v1', 'tenant_key': '2c7e7fb8450f175e', 'app_id': 'cli_a0000e444df89014'}, 'event': {'obj_type': 5, 'task_id': '8346fb5e-60e9-4291-a814-52cb945687dd'}})
