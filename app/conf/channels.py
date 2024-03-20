import ssl
from redis.asyncio.connection import Connection, RedisSSLContext
from typing import Optional
from urllib.parse import urlparse
from .redis import *


if REDIS_SENTINELS:
    # Redis "Sentinel" cluster settings
    sentinels_list = REDIS_SENTINELS.split(',')

    sentinels_tuples = []
    for sentinel_host in sentinels_list:
        host = sentinel_host.split(':')[0]
        port = sentinel_host.split(':')[1]
        sentinels_tuples.append(tuple((host, port)))

    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [
                    {
                        "sentinels": sentinels_tuples,
                        "master_name": REDIS_SENTINEL_MASTER_NAME,
                        "db": 0,
                        "password": REDIS_PASS,
                    }
                ]
            },
        },
    }

elif REDIS_SSL:
    # Secured Redis connection used for DigitalOcean hosted cluster
    class CustomSSLConnection(Connection):
        def __init__(
            self,
            ssl_context: Optional[str] = None,
            **kwargs,
        ):
            super().__init__(**kwargs)
            self.ssl_context = RedisSSLContext(ssl_context)

    url = urlparse(f'rediss://{REDIS_USER}:{REDIS_PASS}@{REDIS_HOST}:{REDIS_PORT}/0')
    ssl_context = ssl.SSLContext()
    ssl_context.check_hostname = False

    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                'hosts': [
                    {
                        'host': url.hostname,
                        'port': url.port,
                        'username': url.username,
                        'password': url.password,
                        'connection_class': CustomSSLConnection,
                        'ssl_context': ssl_context,
                    }
                ],
            },
        },
    }

else:
    # Classic Redis connection
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [f"redis://{REDIS_USER}:{REDIS_PASS}@{REDIS_HOST}:{REDIS_PORT}/0"],
            },
        },
    }
