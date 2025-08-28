import json
import traceback
from typing import Optional

import requests

from util.log_util import logger


class LarkMessage:
    message_id = None
    message_type = ''
    chat_id = None
    # group p2p
    chat_type = ''
    # 原始内容
    content = None
    # 尝试提取plain text
    text = None
    ats = []
    create_timestamp = 0
    user_id = ''
    user_type = ''  # user
    parent_id = ''
    root_id = ''
    user_open_id = ''
    user_union_id = ''


class LarkEmoticon:
    post = True  # False means withdraw
    message_id = None  # emoticon posts at which msg
    create_timestamp = 0
    emoji = ''  # raw name
    user_id = ''
    user_type = ''


class LarkEvent:
    event_id = None
    create_timestamp = 0
    event_type = ''
    app_id = ''
    body_message: Optional[LarkMessage] = None
    body_emoticon: Optional[LarkEmoticon] = None

    def to_json(self):
        result = self.__dict__
        if self.body_message:
            result['body_message'] = self.body_message.__dict__
        if self.body_emoticon:
            result['body_emoticon'] = self.body_emoticon.__dict__
        return result


def tackle_message_event(event):
    url = 'https://your-domain.com'
    if 'event' in event:
        event_info = event['event']
        logger.info('[chat message] detail: {}'.format(event_info))
    try:
        resp = requests.post(url=url, headers={'Content-Type': 'application/json; charset=utf-8'}, data=json.dumps(event))
        if resp:
            resp = resp.text
        logger.info('[transfer chat] resp: {}'.format(resp))
    except:
        logger.error('[transfer chat] error: {}'.format(traceback.format_exc()))

    return None


def parse_event_schema_2(body):
    schema = body.get('schema', None)
    if not schema or int(float(schema)) != 2:
        return False, 'not support schema'
    header = body.get('header', None)
    event = body.get('event', None)
    if not header or not event:
        return False, 'failed to parse event'
    lark_event = LarkEvent()
    lark_event.event_id = header.get('event_id', '')
    lark_event.create_timestamp = int(header.get('create_time', '0'))
    lark_event.event_type = header.get('event_type', '')
    lark_event.app_id = header.get('app_id', '')
    if lark_event.event_type == 'im.message.receive_v1':
        lark_message = LarkMessage()
        lark_message.message_id = event.get('message', {}).get('message_id', '')
        lark_message.message_type = event.get('message', {}).get('message_type', '')
        lark_message.chat_id = event.get('message', {}).get('chat_id', '')
        lark_message.chat_type = event.get('message', {}).get('chat_type', '')
        lark_message.parent_id = event.get('message', {}).get('parent_id', '')
        lark_message.root_id = event.get('message', {}).get('root_id', '')
        lark_message.content = json.loads(event.get('message', {}).get('content', '{}'))
        lark_message.text = json.loads(event.get('message', {}).get('content', '{}')).get('text', '')
        if mentions := event.get('message', {}).get('mentions', []):
            for mention in mentions:
                at_key = mention.get('key', '')
                at_name = mention.get('name', '')
                at_user_id = mention.get('id', {}).get('user_id', '')
                lark_message.text = lark_message.text.replace(at_key, '').strip()
                lark_message.ats.append({'name': at_name, 'user_id': at_user_id})
        lark_message.create_timestamp = int(event.get('message', {}).get('create_time', '0'))
        lark_message.user_id = event.get('sender', {}).get('sender_id', {}).get('user_id', '')
        lark_message.user_type = event.get('sender', {}).get('sender_type', '')
        lark_message.user_open_id = event.get('sender', {}).get('sender_id', {}).get('open_id', '')
        lark_message.user_union_id = event.get('sender', {}).get('sender_id', {}).get('union_id', '')
        lark_event.body_message = lark_message
    elif lark_event.event_type in ['im.message.reaction.created_v1', 'im.message.reaction.deleted_v1']:
        lark_emoticon = LarkEmoticon()
        lark_emoticon.post = lark_event.event_type == 'im.message.reaction.created_v1'
        lark_emoticon.message_id = event.get('message_id', '')
        lark_emoticon.create_timestamp = int(event.get('action_time', '0'))
        lark_emoticon.emoji = event.get('reaction_type', {}).get('emoji_type', '')
        lark_emoticon.user_id = event.get('user_id', {}).get('user_id')
        lark_emoticon.user_type = event.get('operator_type', '')
        lark_event.body_emoticon = lark_emoticon
    # print(lark_event.__dict__)
    # if lark_event.body_message:
    #     print(lark_event.body_message.__dict__)
    #     print(lark_event.body_message.ats)
    # if lark_event.body_emoticon:
    #     print(lark_event.body_emoticon.__dict__)

    return True, lark_event


if __name__ == '__main__':
    b_ = {
        "schema": "2.0",
        "header": {
            "event_id": "ac6134d8cc414fa2126237acf067b1cb",
            "token": "QeH4QN5gzSn0sLP3AT5IUgDbqy8v45rg",
            "create_time": "1681996754960",
            "event_type": "im.message.receive_v1",
            "tenant_key": "2c7e7fb8450f175e",
            "app_id": "cli_a4b52527befad013"
        },
        "event": {
            "message": {
                "chat_id": "oc_2fe8adfc25b65efd2cbd310490765045",
                "chat_type": "group",
                "content": "{\"text\":\"hi 谁能看到我的消息\"}",
                "create_time": "1681996754696",
                "message_id": "om_2822bd889e454d19e4aea5a89c524f92",
                "message_type": "text"
            },
            "sender": {
                "sender_id": {
                    "open_id": "ou_cbd586bc1f96e055999720d7225578ce",
                    "union_id": "on_628cf653584a2d424d6f85cbf0ce10db",
                    "user_id": "dac53d12"
                },
                "sender_type": "user",
                "tenant_key": "2c7e7fb8450f175e"
            }
        }
    }
    c_ = {
        "schema": "2.0",
        "header": {
            "event_id": "44ad9d1d131294a600b1041a34fba157",
            "token": "QeH4QN5gzSn0sLP3AT5IUgDbqy8v45rg",
            "create_time": "1682426104973",
            "event_type": "im.message.receive_v1",
            "tenant_key": "2c7e7fb8450f175e",
            "app_id": "cli_a4b52527befad013"
        },
        "event": {
            "message": {
                "chat_id": "oc_2fe8adfc25b65efd2cbd310490765045",
                "chat_type": "group",
                "content": "{\"text\":\"@_user_1 @_user_2 你们在不\"}",
                "create_time": "1682426104795",
                "mentions": [
                    {
                        "id": {
                            "open_id": "ou_c4690fefe8ab78d79a1c09f0c5cb67f7",
                            "union_id": "on_9f7f993ce617666cdbb246be8f58d42d",
                            "user_id": ""
                        },
                        "key": "@_user_1",
                        "name": "lark_bot",
                        "tenant_key": "2c7e7fb8450f175e"
                    },
                    {
                        "id": {
                            "open_id": "ou_4827c6dca840f4e06bd5619f2bf72c10",
                            "union_id": "on_d7c8b896ad433e6f8757cf24e88fdeec",
                            "user_id": ""
                        },
                        "key": "@_user_2",
                        "name": "idea_bot",
                        "tenant_key": "2c7e7fb8450f175e"
                    }
                ],
                "message_id": "om_8de95b67dbce2ab00ba3b49d427905a8",
                "message_type": "text"
            },
            "sender": {
                "sender_id": {
                    "open_id": "ou_cbd586bc1f96e055999720d7225578ce",
                    "union_id": "on_628cf653584a2d424d6f85cbf0ce10db",
                    "user_id": "dac53d12"
                },
                "sender_type": "user",
                "tenant_key": "2c7e7fb8450f175e"
            }
        }
    }
    d_ = {
        "schema": "2.0",
        "header": {
            "event_id": "736ff3c1359fdf712ec9b9a5ac441833",
            "token": "QeH4QN5gzSn0sLP3AT5IUgDbqy8v45rg",
            "create_time": "1681996662859",
            "event_type": "im.message.reaction.created_v1",
            "tenant_key": "2c7e7fb8450f175e",
            "app_id": "cli_a4b52527befad013"
        },
        "event": {
            "action_time": "1681996662859",
            "message_id": "om_16cbe53de40ec28fee289445456b2238",
            "operator_type": "user",
            "reaction_type": {
                "emoji_type": "THUMBSUP"
            },
            "user_id": {
                "open_id": "ou_cbd586bc1f96e055999720d7225578ce",
                "union_id": "on_628cf653584a2d424d6f85cbf0ce10db",
                "user_id": "dac53d12"
            }
        }
    }
    e_ = {
        "schema": "2.0",
        "header": {
            "event_id": "797a622755fe4b6e987ea89e128b40ff",
            "token": "QeH4QN5gzSn0sLP3AT5IUgDbqy8v45rg",
            "create_time": "1681997415719",
            "event_type": "im.message.reaction.deleted_v1",
            "tenant_key": "2c7e7fb8450f175e",
            "app_id": "cli_a4b52527befad013"
        },
        "event": {
            "action_time": "1681997415719",
            "message_id": "om_2822bd889e454d19e4aea5a89c524f92",
            "operator_type": "user",
            "reaction_type": {
                "emoji_type": "JIAYI"
            },
            "user_id": {
                "open_id": "ou_cbd586bc1f96e055999720d7225578ce",
                "union_id": "on_628cf653584a2d424d6f85cbf0ce10db",
                "user_id": "dac53d12"
            }
        }
    }
    f_ = {'schema': '2.0', 'header': {'event_id': 'c3953a81517df85f40a428b4912b602c', 'token': 'fNePc1FxmmhzG2Ak6GWWz8eLUV68tLWC', 'create_time': '1695194152438', 'event_type': 'im.message.receive_v1', 'tenant_key': '2c7e7fb8450f175e', 'app_id': 'cli_a413263cceba500c'}, 'event': {'message': {'chat_id': 'oc_2fe8adfc25b65efd2cbd310490765045', 'chat_type': 'group', 'content': '{"title":"","content":[[{"tag":"at","user_id":"@_user_1","user_name":"Obs","style":[]},{"tag":"text","text":" /detect","style":[]}],[{"tag":"img","image_key":"img_v2_451522f0-d8b4-491d-8d41-29a77086441g","width":1293,"height":1500}]]}', 'create_time': '1695194152199', 'mentions': [{'id': {'open_id': 'ou_55d5f76c46b0547878169841dcd7ccca', 'union_id': 'on_d33071438490e353526fd2ae2fbbab57', 'user_id': ''}, 'key': '@_user_1', 'name': 'Obs', 'tenant_key': '2c7e7fb8450f175e'}], 'message_id': 'om_435272a0beb2092a3793552b492d5583', 'message_type': 'post', 'update_time': '1695194152199'}, 'sender': {'sender_id': {'open_id': 'ou_37c49f81adeeedf8b454f7db3486e983', 'union_id': 'on_628cf653584a2d424d6f85cbf0ce10db', 'user_id': 'dac53d12'}, 'sender_type': 'user', 'tenant_key': '2c7e7fb8450f175e'}}}
    print(json.dumps(f_))
    o = parse_event_schema_2(f_)
    print(o)
    print(o[1].__dict__['body_message'].__dict__)

