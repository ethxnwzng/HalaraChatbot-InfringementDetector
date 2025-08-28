import os
import traceback

from openai import OpenAI
from home.config import constant
from home.gpt import meta
from lark.settings import BASE_DIR
from util import ffmpeg_util
from util.lark_util import Lark
from util.log_util import logger


FILE_SIZE_MAX = 20 * 1024 * 1024  # MB, openai whisper limits to 25M
client = OpenAI(api_key=meta.OPEN_AI_KEY_AIGC)


def to_text(file_blob=None, file_path=None, retry_max=2):
    if file_blob:
        audio_file = file_blob
    elif file_path:
        del_tmp = False
        file_size = os.path.getsize(file_path)
        is_audio_raw = file_path.endswith('mp3') or file_path.endswith('wav') or file_path.endswith('mpga')
        if file_size > FILE_SIZE_MAX and not is_audio_raw:
            output_path = '{}/home/gpt/data/tmp.mp3'.format(str(BASE_DIR))
            _, mp3_file = ffmpeg_util.convert_video_to_audio_moviepy(file_path, output_path)
            if mp3_file:
                file_path = mp3_file
                del_tmp = True
        audio_file = open(file_path, "rb")
        if del_tmp:
            os.remove(file_path)
    else:
        return False, 'no input'
    retry = 0
    while retry < retry_max:
        retry += 1
        try:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
            if hasattr(transcript, 'text') and transcript.text:
                return True, transcript.text
        except Exception as e:
            logger.error('[openai whisper exception] {}'.format(traceback.format_exc()))
            Lark(constant.LARK_CHAT_ID_P0).send_rich_text('openai whisper exception', traceback.format_exc())

    return False, 'error in parsing, pls retry later or contact Luke.'


if __name__ == '__main__':
    file_input = '/Users/liuqingliang/Downloads/20230325-162627.mp4'
    o = to_text(file_path=file_input)
    print(o)

