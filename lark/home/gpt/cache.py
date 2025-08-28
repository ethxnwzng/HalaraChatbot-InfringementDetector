from home.config import constant
from home.gpt import dev_mode, meta
from home.lark_client import bot
from util import redis_util
from home.gpt import cache_key as key


def set_tone(chat_id, tone_text):
    if tone_text is None:
        return
    redis_util.set_(key.get_tone_key(chat_id), tone_text, 24 * 3600)


def get_tone(chat_id):
    tone_text = redis_util.get(key.get_tone_key(chat_id))
    if tone_text is None:
        _, tone_text = dev_mode.get_tone(chat_id)
        if tone_text is not None:
            set_tone(chat_id, tone_text)
    return tone_text


def del_tone(user_id, prompt_id):
    ok, chats, msg = dev_mode.del_tone(user_id, prompt_id)
    if ok:
        for chat in chats:
            redis_util.del_(key.get_tone_key(chat))
    return ok, msg


def get_chatgpt4_users(force_update=False):
    # ask redis
    cache_users = redis_util.get(key.get_gpt_4_users())
    if cache_users and not force_update:
        users = cache_users.split(constant.COMMA)
    else:
        # ask lark
        _, users_1 = bot.get_chat_members(meta.LARK_CHAT_GPT_4_ADS)
        _, users_2 = bot.get_chat_members(meta.LARK_CHAT_GPT_4_VIP)
        users = list(set(users_1 + users_2))
        redis_util.set_(key.get_gpt_4_users(), constant.COMMA.join(users), 24*3600)
    return users


def get_temp(chat_id):
    # try to get from cache
    temp = redis_util.get(key.get_temperature_key(chat_id))
    if temp is not None:
        try:
            temp = float(temp)
            return temp
        except:
            redis_util.del_(key.get_temperature_key(chat_id))

    return 1


def set_temp(temp, chat_id):
    duration_hour = 24
    duration = duration_hour * 3600
    if not temp or not chat_id:
        return False, 'use default'
    try:
        temp = float(temp)
        if not 0 <= temp <= 2:
            return False, 'wrong input, should be: 0 <= temperature <=2'
    except:
        return False, 'error format of temperature, pls input a float'
    redis_util.set_(key.get_temperature_key(chat_id), temp, duration)
    return True, 'success, temperature {} will effect in {} hours'.format(temp, duration_hour)


if __name__ == '__main__':
    o = get_chatgpt4_users()
    print(len(o), o)

