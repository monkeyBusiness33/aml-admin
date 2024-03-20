from .redis import *


if REDIS_SENTINELS:
    sentinels_list = REDIS_SENTINELS.split(',')
    sentinels_tuples = []
    for sentinel_host in sentinels_list:
        host = sentinel_host.split(':')[0]
        port = sentinel_host.split(':')[1]
        sentinels_tuples.append(tuple((host, port)))

    CACHEOPS_SENTINEL = {
        'locations': sentinels_tuples,
        'service_name': REDIS_SENTINEL_MASTER_NAME,
        'password': REDIS_PASS,
        'socket_timeout': 0.1,
        'db': 7
    }
else:
    CACHEOPS_REDIS = f"redis://{REDIS_USER}:{REDIS_PASS}@{REDIS_HOST}:{REDIS_PORT}/7"

CACHEOPS_DEFAULTS = {
    'timeout': 60*60
}

CACHEOPS = {
    'user.user': {'ops': 'get', 'timeout': 60 * 15},
    'user.role': {'ops': 'get'},
    'user.person': {'ops': 'get'},

    'organisation.OrganisationPeople': {'ops': 'get'},
    'core.amlapplication': {'ops': 'get'},
    'core.ActivityLog': {'ops': 'get'},
    'chat.Conversation': {'ops': 'all'},
    'handling.HandlingRequestFeedback': {'ops': 'all'},


    'auth.permission': {'ops': 'all', 'timeout': 60 * 60},
    'user.CustomNotification': {'ops': 'all', 'timeout': 60 * 60},

    # Do not enable wildcard caching as it produce issues with the signals.
    # Issue: https://github.com/Suor/django-cacheops/issues/466
    # '*.*': {'ops': (), 'timeout': 60*60},
    # '*.*': {'timeout': 60 * 15},
}
