import os
import traceback

from home.config import constant
from lark.settings import IS_PROD
from util import sys_util
from util.lark_util import Lark
from util.log_util import logger

if IS_PROD:
    os.environ['IMAGEIO_FFMPEG_EXE'] = sys_util.get_ffmpeg_exec_file()
    from moviepy.editor import VideoFileClip


def convert_video_to_audio_moviepy(video_file, output_file):
    """Converts video to audio using MoviePy library
    that uses `ffmpeg` under the hood"""
    try:
        logger.info('[ffmpeg video2audio] convert: {}'.format(video_file))
        clip = VideoFileClip(video_file)
        clip.audio.write_audiofile(output_file)
    except:
        logger.error('[ffmpeg video2audio exception] {}'.format(traceback.format_exc()))
        Lark(constant.LARK_CHAT_ID_P0).send_rich_text('[ffmpeg video2audio exception]', traceback.format_exc())
        return False, None
    return True, output_file


if __name__ == '__main__':
    file_input = '/Users/liuqingliang/Downloads/20230325-162627.mp4'
    file_output = '/Users/liuqingliang/Downloads/20230325-162627.mp3'
    convert_video_to_audio_moviepy(file_input, file_output)

