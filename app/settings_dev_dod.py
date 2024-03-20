import os
from .settings_dod import *

LOCAL_DEV_ENV = True

INSTALLED_APPS += [
    "django_extensions",
]

SHELL_PLUS = "ipython"
SHELL_PLUS_PRINT_SQL = True

NOTEBOOK_ARGUMENTS = [
    "--ip",
    "0.0.0.0",
    "--port",
    "7010",
    "--allow-root",
    "--no-browser",
]

IPYTHON_ARGUMENTS = [
    "--ext",
    "django_extensions.management.notebook_extension",
    "--debug",
]

IPYTHON_KERNEL_DISPLAY_NAME = "Django Shell-Plus"

SHELL_PLUS_POST_IMPORTS = [
    ("user.models", ("User",)),
    ("decimal", ("Decimal",)),
    ("datetime", ('datetime', 'date', 'time', 'timedelta')),
    ('django.template.loader', ('get_template', 'render_to_string',)),
    ('django.db.models', ('Count', 'Subquery',
     'Max', 'Min', 'Q', 'F', 'Value', 'CharField', 'IntegerField', 'BooleanField', 'DateField',
                          'Case', 'When', 'OuterRef', 'Exists',)),
    ('django.db.models.functions', ('Coalesce', )),

]

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"


def skip_static_requests(record):
    if record.args[0].startswith('GET /static/'):  # filter whatever you want
        return False
    return True


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        # use Django's built in CallbackFilter to point to your filter
        'skip_static_requests': {
            '()': 'django.utils.log.CallbackFilter',
            'callback': skip_static_requests
        }
    },
    'formatters': {
        # django's default formatter
        'django.server': {
            '()': 'django.utils.log.ServerFormatter',
            'format': '[%(server_time)s] %(message)s',
        }
    },
    'handlers': {
        # django's default handler...
        'django.server': {
            'level': 'INFO',
            'filters': ['skip_static_requests'],  # <- ...with one change
            'class': 'logging.StreamHandler',
            'formatter': 'django.server',
        },
    },
    'loggers': {
        # django's default logger
        'django.server': {
            'handlers': ['django.server'],
            'level': 'INFO',
            'propagate': False,
        },
    }
}
