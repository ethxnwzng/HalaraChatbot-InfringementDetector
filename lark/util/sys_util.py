import platform
import sys
import traceback
from concurrent.futures._base import as_completed
from concurrent.futures.thread import ThreadPoolExecutor

from lark.settings import BASE_DIR
from util.log_util import logger

version = platform.python_version()


def is_python_gte_3p8():
    return float('.'.join(version.split('.')[:2])) >= 3.8


def multi_threads(max_threads, func, args, wait=True):
    result = []
    pool = ThreadPoolExecutor(max_workers=max_threads)
    threads = []
    for arg in args:
        t = pool.submit(func, arg)
        threads.append(t)
        logger.info('thread start: %s' % arg)

    logger.info('主程序运行中...')
    if wait:
        for t in as_completed(threads):
            try:
                resp = t.result()
            except Exception:
                logger.error('error in thread: %s, thread: %s' % (traceback.format_exc(), t))
                continue
            else:
                result.append(resp)
                logger.info('%s done, count: %d' % (resp, len(result)))
        logger.info("所有线程任务完成")
    else:
        logger.info("将异步执行")
    return result


def get_ffmpeg_exec_file():
    os_platform = sys.platform
    if os_platform == 'darwin':
        return '{}/home/static/exec_file/ffmpeg_mac'.format(str(BASE_DIR))
    elif os_platform == 'win32':
        return None
    else:
        return '{}/home/static/exec_file/ffmpeg'.format(str(BASE_DIR))


def is_chinese(char):
    if '\u4e00' <= char <= '\u9fff':
        return True
    else:
        return False


def contain_chinese(text):
    if not text:
        return False
    for char in text:
        if is_chinese(char):
            return True
    return False


if __name__ == '__main__':
    o = contain_chinese('hello你好')
    print(o)

