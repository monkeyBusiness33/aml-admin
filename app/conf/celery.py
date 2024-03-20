from decouple import config as _config
from .redis import *

if REDIS_SENTINELS:
    # Redis "Sentinel" cluster settings
    sentinels_list = REDIS_SENTINELS.split(',')
    celery_url = ''
    for sentinel_host in sentinels_list:
        celery_url += f'sentinel://:{REDIS_PASS}@{sentinel_host}/7;'

    CELERY_BROKER_TRANSPORT_OPTIONS = {'master_name': REDIS_SENTINEL_MASTER_NAME}
    CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS = {'master_name': REDIS_SENTINEL_MASTER_NAME}

elif REDIS_SSL:
    # Secured Redis connection used for DigitalOcean hosted cluster
    celery_url = f"rediss://{REDIS_USER}:{REDIS_PASS}@{REDIS_HOST}:{REDIS_PORT}/7?ssl_cert_reqs=optional"

else:
    # Classic Redis connection
    celery_url = f"redis://{REDIS_USER}:{REDIS_PASS}@{REDIS_HOST}:{REDIS_PORT}/7"

CELERY_BROKER_URL = celery_url
CELERY_RESULT_BACKEND = celery_url
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
BACKGROUND_SCHEDULER = _config("BACKGROUND_SCHEDULER", default=False, cast=bool)
BACKGROUND_SCHEDULER_HOST = _config("BACKGROUND_SCHEDULER_HOST", default='')
CELERY_IMPORTS = ['core.tasks',
                  'handling.utils.staff_notifications',
                  'handling.utils.fuel_booking_notifications', ]
