import requests
from util.log_util import logger
from home.idea_bot import meta
from home.lark_client import bot as lark_bot
from home.lark_client import sender as lark_sender


def send_txt(receive_id_type, receive_id, text):
    headers = meta.get_headers()
    lark_bot.send_txt(receive_id_type, receive_id, text, headers=headers)


def send_text_with_title(receive_id_type, receive_id, title, text, at=None):
    headers = meta.get_headers()
    lark_bot.send_text_with_title(receive_id_type, receive_id, title, text, at=at, headers=headers)


def reply(chat_id, user_id, text, title=None):
    headers = meta.get_headers()
    return lark_sender.reply_text(chat_id, user_id, text, title=title, headers=headers)

def get_file_info_from_msg(msg_id: str, file_key: str) -> dict:
    headers = meta.get_headers()
    info_url = f'https://your-feishu-instance.com'
    params = {'type': 'file'}
    logger.info(f'[get_file_info] Trying files endpoint: {info_url}')
    response = requests.get(info_url, headers=headers, params=params)
    if not response or not response.ok:
        logger.error(f'[get_file_info] failed, resp: {response.text}')
    return response


if __name__ == '__main__':
    # send_text_with_title('user_id', constant.LARK_USER_ID_LUKE, 'title', 'text')
    o = get_file_info_from_msg('om_x100b4bb31d00f5080f3eb439b9ce913', 'file_v3_00n5_fe02f217-e485-46fe-bb3a-90883060ce6g')
    print(type(o.content))

