import os
import socket

from celery import Celery
from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')

app = Celery('app')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# visibility_timeout to prevent task duplication (5259600 - 2 month)
app.conf.broker_transport_options = {"visibility_timeout": 5259600}

# Set custom queue name for non-DEBUG mode
if not settings.DEBUG:
    app.conf.task_default_queue = f'{socket.gethostname()}_queue'

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()
