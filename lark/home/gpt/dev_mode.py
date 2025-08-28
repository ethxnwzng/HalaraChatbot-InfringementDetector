import os
import re
import traceback

import django

from home.lark_client import bot

os.environ['DJANGO_SETTINGS_MODULE'] = 'lark.settings'
django.setup()

from home.config import constant
from home.gpt import cache, meta, cache_key
from home.models import AigcPrompt, ChatTone
from util import redis_util
from util.log_util import logger

CHAT_PREFIX = 'devmode:'
COMMANDS = ['help', 'clear context', 'list tones', 'show tone', 'use #n tone', 'list models', 'use #n model',
            'list recipes', 'show #n recipe', 'set temp [0, 2]', 'show temp']
REPLY_DEVELOPING = 'The feature is still under development, please stay tuned.'
CHATGPT_SYSTEM_PROMPT = 'chatgpt-system'
CHATGPT_USER_PROMPT = 'chatgpt-user'
SCOPE_PUBLIC = 'public'
SCOPE_LARK_USER = 'lark-user'
SCOPE_LARK_GROUP = 'lark-group'
DEFAULT_PROMPT_ID = 1
DEFAULT = 'default'
available_models = [meta.MODEL_CHAT_3_5, meta.MODEL_CHAT_4, meta.MODEL_CHAT_4_TURBO, meta.MODEL_CHAT_4_O]


def reply_in_dev(user_id: str, chat_id: str, text: str):
    text = text.strip().lower()
    if text.startswith(CHAT_PREFIX):
        text = text.replace(CHAT_PREFIX, '', 1).strip()
    pt_use_tone = re.compile(r'^use #(\d+) tone$')
    pt_use_model = re.compile(r'^use #(\d+) model$')
    pt_show_recipe = re.compile(r'^show #(\d+) recipe$')
    pt_set_temp = re.compile('^set temp (.*)$')
    if text == 'help':
        reply = '{} '.format(CHAT_PREFIX) + '\n{} '.format(CHAT_PREFIX).join(COMMANDS)
    elif text == 'clear context':
        logger.info('[chat dev mode] clear context with chat_id: {}'.format(chat_id))
        redis_util.del_(cache_key.get_context_key(chat_id))
        reply = 'Complete. You can start the conversation now.'
    elif text == 'list tones':
        reply, _ = list_tones(user_id, chat_id)
    elif text == 'show tone':
        _, reply = get_tone(chat_id)
    elif mt := pt_use_tone.match(text):
        _, reply = use_tone(mt.group(1), user_id, chat_id)
    elif text == 'list models':
        reply = list_models(user_id, chat_id)
    elif mt := pt_use_model.match(text):
        _, reply = use_model(mt.group(1), chat_id)
    elif text == 'list recipes':
        reply, _ = list_recipes(user_id)
    elif mt := pt_show_recipe.match(text):
        _, reply = show_recipe(mt.group(1), user_id)
    elif text == 'show temp':
        temp = cache.get_temp(chat_id)
        reply = 'current temperature: {}'.format(temp)
    elif mt := pt_set_temp.match(text):
        _, reply = cache.set_temp(mt.group(1), chat_id)

    else:
        reply = 'Unable to recognize. Please confirm your command again.'
    return reply


def list_tones(user_id, chat_id):
    # 1. get public
    public_prompts = AigcPrompt.objects.filter(prompt_type=CHATGPT_SYSTEM_PROMPT, scope_type=SCOPE_PUBLIC,
                                               deleted=constant.NO_IN_DB).order_by('id').all()
    # 2. get lark group's
    group_prompts = []
    group_prompts_all = AigcPrompt.objects.filter(prompt_type=CHATGPT_SYSTEM_PROMPT, scope_type=SCOPE_LARK_GROUP,
                                                  deleted=constant.NO_IN_DB).order_by('id').all()
    map_group_tones = {}

    for each in group_prompts_all:
        if each.scope_id not in map_group_tones:
            map_group_tones[each.scope_id] = []
        map_group_tones[each.scope_id].append(each)
    # 判断组内成员识别权限
    for lark_group in map_group_tones.keys():
        if not lark_group:
            continue
        _, group_users = bot.get_chat_members(lark_group)
        if user_id in group_users:
            group_prompts += map_group_tones[lark_group]
    # 3. get user's
    user_prompts = AigcPrompt.objects.filter(prompt_type=CHATGPT_SYSTEM_PROMPT, scope_type=SCOPE_LARK_USER,
                                             scope_id=user_id, deleted=constant.NO_IN_DB).order_by('id').all()
    # 4. get using tone
    chat_tone = ChatTone.objects.filter(tone_type=CHATGPT_SYSTEM_PROMPT, chat_id=chat_id,
                                        deleted=constant.NO_IN_DB).first()
    using_prompt_id = DEFAULT_PROMPT_ID
    if chat_tone:
        using_prompt_id = chat_tone.prompt_id
    # 4. wrap answer
    lines, reply = [], ''
    for prompt in public_prompts:
        lines.append(prompt)
    for prompt in group_prompts:
        lines.append(prompt)
    for prompt in user_prompts:
        lines.append(prompt)
    hit_using = False
    for i in range(len(lines)):
        tip = ''
        if lines[i].id == using_prompt_id:
            tip = ' (USING)'
            hit_using = True
        reply += '{}. {}{}\n'.format(i+1, lines[i].title, tip)
    # 5. empty using, may not auth to old tone or just old tone deleted, reset to default then.
    if not hit_using and using_prompt_id != DEFAULT_PROMPT_ID:
        redis_util.del_(cache_key.get_tone_key(chat_id))
        chat_tone.prompt_id = DEFAULT_PROMPT_ID
        chat_tone.save()
        reply.replace('1. default', '1. default (USING)')

    return reply, lines


def get_tone(chat_id):
    try:
        prompt_id = DEFAULT_PROMPT_ID
        record = ChatTone.objects.filter(tone_type=CHATGPT_SYSTEM_PROMPT, chat_id=chat_id,
                                         deleted=constant.NO_IN_DB).first()
        if record:
            prompt_id = record.prompt_id
        tone = AigcPrompt.objects.filter(id=prompt_id).first()
        return tone.title, tone.detail.get('text', '')
    except:
        logger.error('[chat get tone exception] {}'.format(traceback.format_exc()))
    return None, None


def del_tone(user_id, prompt_id):
    use_chats = []
    if not user_id or not prompt_id:
        return False, use_chats, 'empty params'
    try:
        tone = AigcPrompt.objects.filter(id=prompt_id).first()
        if not tone:
            return False, use_chats, 'no this prompt_id'
        if tone.scope_type != 'lark-user':
            return False, use_chats, 'not support scope_type'
        if tone.scope_id != user_id:
            return False, use_chats, 'not authorized'
        chats = ChatTone.objects.filter(prompt_id=prompt_id).all()
        for each in chats:
            use_chats.append(each.chat_id)
            each.deleted = constant.YES_IN_DB
            each.save()
        tone.deleted = constant.YES_IN_DB
        tone.save()
    except:
        logger.error('[chat del tone exception] {}'.format(traceback.format_exc()))

    return True, use_chats, ''


def del_recipe(user_id, prompt_id):
    if not user_id or not prompt_id:
        return False, 'empty params'
    try:
        recipe = AigcPrompt.objects.filter(id=prompt_id).first()
        if not recipe:
            return False, 'no this prompt_id'
        if recipe.scope_type != 'lark-user':
            return False, 'not support scope_type'
        if recipe.scope_id != user_id:
            return False, 'not authorized'
        recipe.deleted = constant.YES_IN_DB
        recipe.save()
    except:
        logger.error('[chat del recipe exception] {}'.format(traceback.format_exc()))

    return True, ''


def use_tone(index, use_id, chat_id):
    # 1. get all tones list and locate obj tone
    _, tones = list_tones(use_id, chat_id)
    obj_tone_id, obj_tone_title, obj_tone_text = None, None, None
    for i in range(len(tones)):
        if i+1 == int(index):
            obj_tone_id = tones[i].id
            obj_tone_title = tones[i].title
            obj_tone_text = tones[i].detail.get('text', None)
    if not obj_tone_id:
        return False, 'Index not available in "list tones"'

    # 2. get using tone
    tone_id = DEFAULT_PROMPT_ID
    tone_using = ChatTone.objects.filter(tone_type=CHATGPT_SYSTEM_PROMPT, chat_id=chat_id).first()
    if tone_using and tone_using.deleted == constant.NO_IN_DB:
        tone_id = tone_using.prompt_id

    # 3. update obj tone
    if tone_id == obj_tone_id:
        return False, 'We are already here:)'
    cache.set_tone(chat_id, obj_tone_text)
    if tone_using:
        tone_using.prompt_id = obj_tone_id
        tone_using.user_id_update = use_id
        tone_using.deleted = constant.NO_IN_DB
        tone_using.save()
    else:
        ChatTone(tone_type=CHATGPT_SYSTEM_PROMPT, chat_id=chat_id, prompt_id=obj_tone_id, user_id_create=use_id,
                 user_id_update=use_id, deleted=constant.NO_IN_DB).save()

    return True, 'My tone is set to "{}"'.format(obj_tone_title)


def list_models(user_id, chat_id):
    # check cache
    using_model = get_model(user_id, chat_id)
    if not using_model:
        using_model = meta.MODEL_CHAT
    result = ''
    for i in range(len(available_models)):
        model = available_models[i]
        if model == using_model:
            model += ' (USING)'
        result += '{}. {}\n'.format(i + 1, model)
    return result


def use_model(index, chat_id):
    index = int(index)
    if index <= 0 or index > len(available_models):
        return False, 'Index not available in "list models"'
    obj_model = available_models[index-1]
    redis_util.set_(cache_key.get_model_key(chat_id), obj_model, 2*3600)
    return True, 'Success, {} will apply for 2 hours, then reset to default model'.format(obj_model)


def get_model(user_id, chat_id):
    model = meta.MODEL_CHAT
    appoint_model = redis_util.get(cache_key.get_model_key(chat_id))
    if appoint_model:
        model = appoint_model
    return model


def list_recipes(user_id):
    # 1. get public
    public_prompts = AigcPrompt.objects.filter(prompt_type=CHATGPT_USER_PROMPT, scope_type=SCOPE_PUBLIC,
                                               deleted=constant.NO_IN_DB).order_by('id').all()
    # 2. get user's
    user_prompts = AigcPrompt.objects.filter(prompt_type=CHATGPT_USER_PROMPT, scope_type=SCOPE_LARK_USER,
                                             scope_id=user_id, deleted=constant.NO_IN_DB).order_by('id').all()
    # 3. wrap answer
    lines, reply = [], ''
    for prompt in public_prompts:
        lines.append(prompt)
    for prompt in user_prompts:
        lines.append(prompt)
    for i in range(len(lines)):
        reply += '{}. {}\n'.format(i + 1, lines[i].title)
    return reply, lines


def show_recipe(index, user_id):
    index = int(index)
    hit, reply = False, ''
    # get all recipes list and locate obj tone
    _, recipes = list_recipes(user_id)
    if index <= 0 or index > len(recipes):
        return False, 'Index not available in "list recipes"'
    obj_recipe = recipes[index-1]
    reply = obj_recipe.detail.get('text', '')
    return hit, reply


if __name__ == '__main__':
    # order = 'devmode: help'
    # order = 'devmode: list recipes'
    # order = 'devmode: show temp'
    order = 'devmode: set temp 3'
    o = reply_in_dev(constant.LARK_USER_ID_LUKE, 'chat_id', order)
    print(o)

