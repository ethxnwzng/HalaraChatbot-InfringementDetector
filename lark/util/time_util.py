import datetime

import pytz
from django.utils import timezone

from lark import settings
from util import sys_util

TIMEZONE_BJ = 'Asia/Shanghai'
TIME_ZONE = settings.TIME_ZONE
TIME_FORMAT_DEFAULT = '%Y-%m-%d %H:%M:%S'
TIME_FORMAT_ZONE_BJ = '%Y-%m-%dT%H:%M:%S+08:00'
TIME_FORMAT_ZONE = '%Y-%m-%dT%H:%M:%S%z'
DATE_FORMAT_DEFAULT = '%Y-%m-%d'
DATE_FORMAT_COMPACT = '%Y%m%d'


# %Y-%m-%d %H:%M:%S string
def get_cnt_time(time_str, time_format=None):
    if time_format is None:
        time_format = TIME_FORMAT_DEFAULT
    t = timezone.datetime.strptime(time_str, time_format)
    return pytz.timezone(TIME_ZONE).localize(t)


def get_cnt_now():
    t = datetime.datetime.now()
    return pytz.timezone(TIME_ZONE).localize(t)


def to_utc(time_str, time_format=None):
    if time_format is None:
        tz = '+08:00'
        time_format = TIME_FORMAT_DEFAULT
    else:
        tz = time_format.split('%S')[-1]
    if tz == '%z':
        if sys_util.is_python_gte_3p8():
            return datetime.datetime.strptime(time_str, time_format)
        # self parse
        tz = time_str[-6:]
        time_format = time_format.replace('%z', tz)

    bigger_than_utc = True
    if '-' in tz:
        bigger_than_utc = False
    hours = int(tz.lstrip('+-').split(':')[0])
    t = timezone.datetime.strptime(time_str, time_format)
    if bigger_than_utc:
        t -= datetime.timedelta(hours=hours)
    else:
        t += datetime.timedelta(hours=hours)

    return pytz.timezone('UTC').localize(t)


def get_cnt_today():
    return datetime.datetime.now().astimezone(pytz.timezone(TIME_ZONE)).date()


def get_cnt_date(date_str, date_format=None):
    if date_format is None:
        date_format = DATE_FORMAT_DEFAULT
    t = timezone.datetime.strptime(date_str, date_format)
    return t.astimezone(pytz.timezone(TIME_ZONE)).date()


def get_cnt_min_time():
    return get_cnt_time('1970-01-02 08:00:01')


def get_cnt_min_date():
    return get_cnt_date('1970-01-02')


# utc秒数
def get_cnt_from_timestamp(seconds):
    t = datetime.datetime.fromtimestamp(seconds)
    return pytz.timezone('UTC').localize(t)


# utc秒数
def get_cnt_bj_from_timestamp(seconds):
    t = datetime.datetime.fromtimestamp(seconds)
    return pytz.timezone(TIME_ZONE).localize(t)


# print(get_cnt_time('2020-11-21 09:12:41'))
# print(get_cnt_now())
# print(get_cnt_now_date())
