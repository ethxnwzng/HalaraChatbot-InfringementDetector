

def get_context_key(chat_id):
    return 'chat_gpt:context:{}'.format(chat_id)


def get_tone_key(chat_id):
    return 'chat_gpt:tone:{}'.format(chat_id)


def get_model_key(chat_id):
    return 'chat_gpt:model:{}'.format(chat_id)


def get_gpt_4_users():
    return 'chat_gpt:4:users'


def get_temperature_key(chat_id):
    return 'chat_gpt:temperature:{}'.format(chat_id)

