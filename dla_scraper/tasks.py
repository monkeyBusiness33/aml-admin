import pytz

from celery import shared_task
from celery.utils.log import get_task_logger
from datetime import datetime
from app.celery import app as celery_app
from .models import DLAScraperRun

logger = get_task_logger(__name__)


@shared_task
def run_dla_scraper_task(scheduled=True):
    from dla_scraper.utils.scraper import run_dla_scraper
    run_dla_scraper(scheduled)

@shared_task
def check_previous_scraper_run():
    # Check if the latest SUCCESSFUL scheduled run was not more than 12 hours ago
    successful_scheduled_runs = DLAScraperRun.objects.filter(is_scheduled=True).exclude(status__code="ERROR")

    if not successful_scheduled_runs:
        return

    last_run = successful_scheduled_runs.latest('run_at')
    time_delta = datetime.now().replace(tzinfo=pytz.utc) - last_run.run_at

    if time_delta.total_seconds() > 3600 * 12:
        run_dla_scraper_task()
