import time
import traceback
from openai import OpenAI

from home.config import constant
from home.gpt import meta
from util.lark_util import Lark
from util.log_util import logger


DEFAULT_SYS_PROMPT = """
You are ChatGPT, a large language model trained by OpenAI, based on the {} architecture.
"""


def get_default_sys_prompt(model):
    return DEFAULT_SYS_PROMPT.format(str(model).upper()).strip()


def ask(prompt_list, system_prompt='', model=meta.MODEL_CHAT_3_5, temperature=0.7, auto_retry=False):
    if not prompt_list:
        return False, ''
    retry_max = 3 if auto_retry else 1
    retry = 0
    while retry < retry_max:
        retry += 1
        try:
            client = OpenAI(api_key=meta.OPEN_AI_KEY_AIGC)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            for prompt in prompt_list:
                role, content = 'user', prompt
                if '::' in prompt:
                    role, content = prompt.split('::', 1)
                messages.append({"role": role, "content": content})
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature
            )
            if response and response.choices and response.choices[0].message:
                return True, response.choices[0].message.content
        except Exception as e:
            logger.error('[openai chat exception] {}'.format(traceback.format_exc()))
            Lark(constant.LARK_CHAT_ID_P0).send_rich_text('openai chat exception', traceback.format_exc())
            if not auto_retry:
                break
            time.sleep(1)

    return False, 'error in parsing, please retry later or contact Luke.'


if __name__ == '__main__':
    prompt_ = ['user::hi']
    success, response = ask(prompt_, model=meta.MODEL_CHAT_3_5)
    print(f"Success: {success}")
    print(f"Response: {response}")

