from home.lark_client.bot import send_msg


def reply_text(chat_id, user_id, text, title=None, headers=None):
    receive_id_type = ''
    receive_id = ''
    if chat_id:
        receive_id_type = 'chat_id'
        receive_id = chat_id
    elif user_id:
        receive_id_type = 'user_id'
        receive_id = user_id
    content_type = 'text'
    content = {'text': text}
    if title:
        content_type = 'post'
        content = {"zh_cn": {
                    "title": title,
                    "content": [
                        [
                            {
                                "tag": "text",
                                "text": text
                            }
                        ]
                    ]
                }}

    return send_msg(receive_id_type, receive_id, content_type, content, headers=headers)

