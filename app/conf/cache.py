from .redis import *

CACHES = {}

SELECT2_REDIS_TIMEOUT = 28800

if REDIS_SENTINELS:
    # Redis "Sentinel" cluster settings
    DJANGO_REDIS_CONNECTION_FACTORY = 'django_redis.pool.SentinelConnectionFactory'

    sentinels_list = REDIS_SENTINELS.split(',')
    sentinels_tuples = []
    for sentinel_host in sentinels_list:
        host = sentinel_host.split(':')[0]
        port = sentinel_host.split(':')[1]
        sentinels_tuples.append(tuple((host, port)))

    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": f'redis://{REDIS_SENTINEL_MASTER_NAME}:{REDIS_PORT}/7',
            "OPTIONS": {
                "SENTINELS": sentinels_tuples,
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "PASSWORD": REDIS_PASS,
                "CONNECTION_POOL_CLASS": "redis.sentinel.SentinelConnectionPool"
            }
        },
        "select2": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": f'redis://{REDIS_SENTINEL_MASTER_NAME}:{REDIS_PORT}/8',
            "TIMEOUT": SELECT2_REDIS_TIMEOUT,
            "OPTIONS": {
                "SENTINELS": sentinels_tuples,
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "PASSWORD": REDIS_PASS,
                "CONNECTION_POOL_CLASS": "redis.sentinel.SentinelConnectionPool"
            }
        }
    }
else:
    protocol = 'rediss' if REDIS_SSL else 'redis'
    params = '?ssl_cert_reqs=optional' if REDIS_SSL else ''
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": f"{protocol}://{REDIS_USER}:{REDIS_PASS}@{REDIS_HOST}:{REDIS_PORT}/7{params}",
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            }
        },
        "select2": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": f"{protocol}://{REDIS_USER}:{REDIS_PASS}@{REDIS_HOST}:{REDIS_PORT}/8{params}",
            "TIMEOUT": SELECT2_REDIS_TIMEOUT,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            }
        }
    }

if CACHES:
    SELECT2_CACHE_BACKEND = 'select2'
    SOLO_CACHE = 'default'
