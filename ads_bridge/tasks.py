from celery import shared_task
from celery.utils.log import get_task_logger
from .sync import *
logger = get_task_logger(__name__)


# @shared_task
# def sync_ads_all():
#     sync_ads_countries()
#     sync_ads_regions()
#     sync_ads_airports()
#     sync_ads_aircraft()
