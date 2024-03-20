from decouple import config as _config

LOGTAIL_SOURCE_TOKEN = _config("LOGTAIL_SOURCE_TOKEN", default='')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'logtail': {
            'class': 'logtail.LogtailHandler',
            'source_token': LOGTAIL_SOURCE_TOKEN,
        },
    },
    'loggers': {
        '': {
            'handlers': [
                'console',
                'logtail',
            ],
            'level': 'INFO'
        },
        'daphne': {
            'handlers': [
                'console',
            ],
            'level': 'INFO'
        },
    },
}
