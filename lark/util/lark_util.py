import requests
import json
from util.log_util import logger

headers = {'Content-Type': 'application/json'}


class Lark:
    def __init__(self, url):
        self.url = url

    def send_text(self, text):
        data = {"msg_type": "text", "content": {
            "text": text}}
        resp = requests.post(self.url, headers=headers, data=json.dumps(data))
        logger.info("[lark] send text: %s, resp: %s" % (text.replace('\n', ' '), resp.text))

    def send_rich_text(self, title, content):
        data = {"msg_type": "post", "content": {
            "post": {
                "zh_cn": {
                    "title": title,
                    "content": [
                        [
                            {
                                "tag": "text",
                                "text": content
                            }
                        ]
                    ]
                }
            }}}
        resp = requests.post(self.url, headers=headers, data=json.dumps(data))
        logger.info("[lark] send rich title: %s, content: %s, resp: %s" % (title, content.replace('\n', ' '), resp.text))

