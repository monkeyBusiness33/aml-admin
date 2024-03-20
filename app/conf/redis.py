from decouple import config as _config


REDIS_HOST = _config('REDIS_HOST', 'localhost')
REDIS_PORT = _config('REDIS_PORT', default=6379)
REDIS_USER = _config('REDIS_USER', default='')
REDIS_PASS = _config('REDIS_PASS', default='')
REDIS_SENTINELS = _config('REDIS_SENTINELS', default='')
REDIS_SENTINEL_MASTER_NAME = _config('REDIS_SENTINEL_MASTER_NAME', default='mymaster')

# Signalise remote Redis connection such as DigitalOcean hosted Redis
REDIS_SSL = _config('REDIS_SSL', cast=bool, default=False)
