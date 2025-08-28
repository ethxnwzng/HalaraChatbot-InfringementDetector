from apscheduler.schedulers.background import BackgroundScheduler

from . import bu_cs
from .crawler import halara_crawler_job
from lark.settings import IS_PROD, TIME_ZONE
from util.log_util import logger


def init():
    logger.info('launch background scheduler')
    scheduler = BackgroundScheduler(timezone=TIME_ZONE)
    if IS_PROD:
        scheduler.add_job(func=bu_cs.cron_check_approval, trigger='cron', second='18', minute='3', hour='*')
        # Add Halara crawler job - runs daily at 2 AM
        scheduler.add_job(func=halara_crawler_job.run_crawler, trigger='cron', hour='2', minute='0')

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info('shutdown background scheduler')


