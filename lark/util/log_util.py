import logging
from lark.settings import IS_PROD, BASE_DIR
import sys

os_platform = sys.platform

# 第一步，创建一个logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)  # Log等级总开关

# 第二步，创建一个handler，用于写入日志文件
if IS_PROD:
    logfile = '/data/logs/lark/lark.log'
elif os_platform == 'win32':
    logfile = '/data/logs/lark/lark.log'
else:
    logfile = str(BASE_DIR) + '/lark.log'
# fh = logging.FileHandler(logfile, mode='a')
# fh.setLevel(logging.DEBUG)  # 用于写到file的等级开关

# 第三步，再创建一个handler,用于输出到控制台
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)  # 输出到console的log等级的开关

# 第四步，定义handler的输出格式
formatter = logging.Formatter('%(asctime)s [%(thread)d] [%(threadName)s] %(levelname)s %(module)s - %(message)s')
# fh.setFormatter(formatter)
ch.setFormatter(formatter)

# 第五步，将logger添加到handler里面
# logger.addHandler(fh)
logger.addHandler(ch)
