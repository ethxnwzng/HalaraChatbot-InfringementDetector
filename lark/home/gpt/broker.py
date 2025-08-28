import traceback

from home.config import constant
from home.gpt import chat_client, meta, dev_mode, cache, cache_key
from home.lark_client import sender
from home.models import ChatMsg
from util import redis_util, sys_util
from util.lark_util import Lark
from util.log_util import logger


def ask(body):
    if not body or 'event' not in body:
        return None
    event = body['event']
    msg_id = event.get('open_message_id', '')
    chat_type = event.get('chat_type', '')
    user_id = event.get('employee_id', '')
    is_mention = event.get('is_mention', False)
    if is_mention:
        at_bot = constant.YES_IN_DB
    else:
        at_bot = constant.NO_IN_DB
    if chat_type == 'group' and not is_mention:
        # 群聊只关注直接at机器人消息
        return None
    msg_type = event.get('msg_type', '')
    chat_id = event.get('open_chat_id', '')
    open_id = event.get('open_id', '')
    union_id = event.get('union_id', '')
    msg_parent_id = event.get('parent_id', '')
    msg_root_id = event.get('root_id', '')
    text_without_at_bot = event.get('text_without_at_bot', '')
    if text_without_at_bot is None:
        return None
    text_without_at_bot = str(text_without_at_bot)
    user_agent = event.get('user_agent', '')
    msg_receive = {'text': text_without_at_bot, 'user_agent': user_agent}

    # 判断是否进入dev_mode
    is_dev_mode, direction_ask, direction_reply = constant.NO_IN_DB, 'receive', 'chat_gpt'
    if text_without_at_bot.strip().lower().startswith(dev_mode.CHAT_PREFIX):
        is_dev_mode = constant.YES_IN_DB
        direction_reply = 'send'

    # 判断用来执行的模型
    model = dev_mode.get_model(user_id, chat_id)

    # 记录消息
    try:
        ChatMsg(msg_id=msg_id, direction=direction_ask, msg_type=msg_type, chat_type=chat_type, chat_id=chat_id,
                at_bot=at_bot, user_id=user_id, open_id=open_id, union_id=union_id, msg_parent_id=msg_parent_id,
                msg_root_id=msg_root_id, msg=msg_receive, deleted=constant.NO_IN_DB, dev_mode=is_dev_mode,
                chat_bot=meta.CHAT_BOT_NAME).save()
    except:
        logger.error('[chat write msg exception]: {}'.format(traceback.format_exc()))
        Lark(constant.LARK_CHAT_ID_P0).send_rich_text('chat write exception', traceback.format_exc())

    if is_dev_mode:
        model = 'sys'
        reply = dev_mode.reply_in_dev(user_id, chat_id, text_without_at_bot)
    else:
        # 进入chatGPT
        hit, reply = do_ask_with_context(chat_id, text_without_at_bot, model=model)
        if hit is None:
            # 上下文过载，先自动清空
            hit, reply = do_ask_with_context(chat_id, text_without_at_bot, reset=True, model=model)
            if hit is None:
                # 仍过载就是本身问题太长，无法处理
                reply = '上下文过载，无法处理(reach maximum context length, cannot handle it)'
            elif hit:
                reply = '[上下文过载，已重置(reach maximum context length, have reset)]\n{}'.format(reply)

    # 发送回答
    try:
        reply_msg_id, reply_msg_type = '', ''
        if not reply:
            reply = "That's empty in my mind."
        reply_resp = sender.reply_text(chat_id, user_id, reply)
        if reply_resp and 'data' in reply_resp and 'message_id' in reply_resp['data'] and 'msg_type' in reply_resp['data']:
            reply_msg_id = reply_resp['data']['message_id']
            reply_msg_type = reply_resp['data']['msg_type']
        msg_reply = {'text': reply, 'replier': model}
        # 记录回答
        ChatMsg(msg_id=reply_msg_id, direction=direction_reply, msg_type=reply_msg_type, chat_type=chat_type, chat_id=chat_id,
                at_bot=constant.NO_IN_DB, user_id=user_id, open_id='', union_id='', msg_parent_id=msg_id,
                msg_root_id='', msg=msg_reply, deleted=constant.NO_IN_DB, dev_mode=is_dev_mode, chat_bot=meta.CHAT_BOT_NAME).save()
    except:
        logger.error('[chat reply exception]: {}'.format(traceback.format_exc()))
        Lark(constant.LARK_CHAT_ID_P0).send_rich_text('chat reply exception', traceback.format_exc())
    return True


def do_ask_with_context(chat_id, content, reset=False, model=meta.MODEL_CHAT):
    redis_key = cache_key.get_context_key(chat_id)
    each_chat_user = 'user::{}'.format(content)
    if reset:
        redis_util.del_(redis_key)
    redis_util.rpush(redis_key, each_chat_user)
    redis_util.expire(redis_key, meta.TIMEOUT_CHAT_CONTEXT)
    prompt_list = redis_util.lrange(redis_key, 0, -1)
    # reply
    system_prompt = cache.get_tone(chat_id)
    temperature = cache.get_temp(chat_id)
    hit, reply = chat_client.ask(prompt_list, system_prompt=system_prompt, model=model, temperature=temperature)
    # 写入回复上下文
    if hit:
        each_chat_bot = 'assistant::{}'.format(reply)
        redis_util.rpush(redis_key, each_chat_bot)
        redis_util.expire(redis_key, meta.TIMEOUT_CHAT_CONTEXT)
    return hit, reply

