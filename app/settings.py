from pathlib import Path
import os
from django.contrib.messages import constants as messages
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from decouple import config
from firebase_admin import initialize_app, credentials
import app.utils.colored_logger

from app.conf.channels import CHANNEL_LAYERS
from app.conf.celery import *
from app.conf.redis import *
from app.conf.logging import LOGGING
from app.conf.cache import *
from app.conf.django_flatpickr import *
from app.conf.cacheops import *


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = Path(__file__).parent

SECRET_KEY = config('SECRET_KEY', default='S#perS3crEt_1122')
DEBUG = config('DEBUG', default=False, cast=bool)
ENABLE_DEBUG_TOOLBAR = config('ENABLE_DEBUG_TOOLBAR', default=False, cast=bool)
ALLOWED_HOSTS = ['localhost', '127.0.0.1', config('DOMAIN', default='localhost')] if not DEBUG else ['*']
AML_OPERATIONS_PORTAL_DOMAIN = config('DOMAIN', default='localhost')
AML_DOD_PORTAL_DOMAIN = config('AML_DOD_PORTAL_DOMAIN', default='localhost')

DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50 MB

# Generate CSRF_TRUSTED_ORIGINS from the ALLOWED_HOSTS
CSRF_TRUSTED_ORIGINS = []
for hostname in ALLOWED_HOSTS:
    CSRF_TRUSTED_ORIGINS.append(f'http://{hostname}')
    CSRF_TRUSTED_ORIGINS.append(f'https://{hostname}')


DATABASE_ROUTERS = ['app.dbrouters.CustomDBRouter', ]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='aml_v2_dev'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASS', default=''),
        'HOST': config('DB_HOST', default='127.0.0.1'),
        'PORT': config('DB_PORT', default='5000'),
    },
    'default_replica': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='aml_v2_dev'),
        'USER': config('DB_USER', default='aml_v2_dev'),
        'PASSWORD': config('DB_PASS', default=''),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5004'),
    },
    'ads': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('ADS_DB_NAME', default='ads_live'),
        'USER': config('ADS_DB_USER', default='ads_live'),
        'PASSWORD': config('ADS_DB_PASS', default='ads_live'),
        'HOST': config('ADS_DB_HOST', default='localhost'),
        'PORT': config('ADS_DB_PORT', default='3306'),
    },
}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
DB_PREFIX = 'new_'

# Application definition
INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django_otp',
    'django_otp.plugins.otp_static',
    'django_otp.plugins.otp_totp',
    'two_factor',
    'ajax_datatable',
    'bootstrap_modal_forms',
    'django_select2',
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_json_api',
    'notifications',
    'fcm_django',
    'captcha',
    'solo',
    'tagify',
    'channels',
    'corsheaders',
    'django_flatpickr',
    'cacheops',

    'user',
    'administration',
    'organisation',
    'core',
    'aircraft',
    'api',
    'handling',
    'mission',
    'pricing',
    'staff',
    'ads_bridge',
    'crm',
    'dod_portal',
    'frontpage',
    'dla_scraper',
    'supplier',
    'chat',
    'amlopsvueelements',
]
AUTH_USER_MODEL = 'user.User'
NOTIFICATIONS_NOTIFICATION_MODEL = 'user.CustomNotification'


### PUSH notifications section start
FIREBASE_KEY_B64 = config('FIREBASE_KEY_B64', default='')
if FIREBASE_KEY_B64:
    cred = credentials.Certificate(os.path.join(BASE_DIR, "fcm.json"))
    FIREBASE_APP = initialize_app(cred)

    FCM_DJANGO_SETTINGS = {
        "UPDATE_ON_DUPLICATE_REG_ID": True,
    }

### PUSH notifications section end

CORS_ALLOW_ALL_ORIGINS = True

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_downloadview.SmartDownloadMiddleware',
    'app.middlewares.OpsPortalMiddleware'
]

DATA_UPLOAD_MAX_NUMBER_FIELDS = 10240
SESSION_COOKIE_NAME = 'aml_session'
LOGIN_URL = 'admin:login'
LOGIN_REDIRECT_URL = 'admin:organisations'
LOGIN_REDIRECT_URL_MILITARY_TEAM_ROLE = 'admin:handling_requests'
LOGIN_REDIRECT_URL_MILITARY_OBSERVER_TEAM_ROLE = 'admin:handling_requests_calendar'
LOGOUT_REDIRECT_URL = 'admin:login'
ENFORCE_TWO_FACTOR = True

TWO_FACTOR_PATCH_ADMIN = False
AUTHENTICATION_BACKENDS = [
    'user.backends.AMLUserBackend',
    # Disable default Django backend
    # 'django.contrib.auth.backends.ModelBackend'
]
# PASSWORD_HASHERS = [
#     # 'django.contrib.auth.hashers.PBKDF2PasswordHasher',
#     # 'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
#     # 'django.contrib.auth.hashers.Argon2PasswordHasher',
#     # 'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
#     # 'django.contrib.auth.hashers.BCryptPasswordHasher',
#     'django.contrib.auth.hashers.UnsaltedMD5PasswordHasher',
# ]

ROOT_URLCONF = 'app.urls'
TEMPLATE_DIR = os.path.join(BASE_DIR, "app/templates")  # ROOT dir for templates

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [TEMPLATE_DIR],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.shared_api_keys',
            ],
        },
    },
]

WSGI_APPLICATION = 'app.wsgi.application'
ASGI_APPLICATION = 'app.asgi.application'


# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# DRF settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'api.auth_class.BearerTokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],

    # JSON:API settings
    'PAGE_SIZE': 10,
    'EXCEPTION_HANDLER': 'api.exceptions.json_api_exception_handler',
    'DEFAULT_PAGINATION_CLASS':
        'rest_framework_json_api.pagination.JsonApiPageNumberPagination',
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework_json_api.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser'
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework_json_api.renderers.JSONRenderer',
        # 'rest_framework_json_api.renderers.BrowsableAPIRenderer',
    ),
    'DEFAULT_METADATA_CLASS': 'rest_framework_json_api.metadata.JSONAPIMetadata',
    'DEFAULT_FILTER_BACKENDS': (
        'rest_framework_json_api.filters.QueryParameterValidationFilter',
        'rest_framework_json_api.filters.OrderingFilter',
        'rest_framework_json_api.django_filters.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
    ),
    'SEARCH_PARAM': 'filter[search]',
    'TEST_REQUEST_RENDERER_CLASSES': (
        'rest_framework_json_api.renderers.JSONRenderer',
    ),
    'TEST_REQUEST_DEFAULT_FORMAT': 'vnd.api+json'
}


# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True
USE_TZ = True

DATE_INPUT_FORMATS = ['%Y-%m-%d', ]
DATETIME_INPUT_FORMATS = ['%Y-%m-%d %H:%M:%S', ]

MESSAGE_TAGS = {
    messages.DEBUG: 'info',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'error',
}

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

STATIC_CDN = config('STATIC_CDN', default=False, cast=bool)

if STATIC_CDN:
    STATIC_CDN_CUSTOM_DOMAIN = config('STATIC_CDN_CUSTOM_DOMAIN')
    STATIC_URL = f'https://{STATIC_CDN_CUSTOM_DOMAIN}/'
else:
    STATIC_URL = '/static/'

STATICFILES_STORAGE = 'app.utils.staticfiles_storage.NoSourceMapsStorage'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_ROOT = os.path.join(BASE_DIR, 'frontpage/static')
DOCS_ROOT = os.path.join(BASE_DIR, 'document_files')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'app/static'),
)

DEFAULT_FILE_STORAGE = 'django_downloadview.storage.SignedStorage'

SELECT2_JS = '/static/assets/vendor/select2/select2.min.js'
SELECT2_CSS = '/static/assets/vendor/select2/select2.min.css'


DOWNLOADVIEW_BACKEND = "django_downloadview.nginx.XAccelRedirectMiddleware"
DOWNLOADVIEW_RULES = [
    # {
    #     "source_url": "/media/nginx/",
    #     "destination_url": "/nginx-optimized-by-middleware/",
    # },
]

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='localhost')
EMAIL_PORT = config('EMAIL_PORT', default='1025')
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
EMAIL_FROM_ADDRESS = config('EMAIL_FROM_ADDRESS', default='AML Global Limited <ops@amlglobal.net>')

CONTACTUS_MAILTO = config('CONTACTUS_MAILTO',
                          default='fuelteam@amlglobal.net')
CONTACTUS_MAILCC = config('CONTACTUS_MAILCC',
                          default='amlsupport@amlglobal.net')

sentry_sdk.init(
    dsn=os.environ.get('SENTRY_DSN'),
    integrations=[DjangoIntegration(), RedisIntegration()],
    traces_sample_rate=0.20,
    send_default_pii=True,
    environment=config("SENTRY_ENV", 'dev')
)

AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default='')
AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', 'eu-central-1')
AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME', default='')
AWS_S3_CUSTOM_DOMAIN = '%s.s3.amazonaws.com' % AWS_STORAGE_BUCKET_NAME
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
    'ContentDisposition': 'attachment'
}

# AML Emails configuration
EMAIL_AML_SPF = config('EMAIL_AML_SPF', default='denis.verbin+spf@aviationdata.aero')
WHAT3WORDS_API_KEY = config('WHAT3WORDS_API_KEY', default='')
GOOGLE_MAPS_API_KEY = config('GOOGLE_MAPS_API_KEY', default='')
OFAC_API_KEY = config('OFAC_API_KEY', default='')

RECAPTCHA_PUBLIC_KEY = config('RECAPTCHA_PUBLIC_KEY',
                              default='6LfzLIoaAAAAAKCqC06j5LcNhsA2PXcW8OAL4lYU')
RECAPTCHA_PRIVATE_KEY = config('RECAPTCHA_PRIVATE_KEY',
                               default='6LfzLIoaAAAAAMDvjOj4Ih27g8iBY3XBk6bi2Up0')
RECAPTCHA_DEFAULT_ACTION = 'generic'
RECAPTCHA_SCORE_THRESHOLD = 0.5
SILENCED_SYSTEM_CHECKS = ['captcha.recaptcha_test_key_error']
FRONTPAGE_ENABLED = config('FRONTPAGE_ENABLED', default=True, cast=bool)


TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN', default='')
TWILIO_SENDER_NUMBER = config('TWILIO_SENDER_NUMBER', default='+14155238886')

FIREBASE_API_KEY = config('FIREBASE_API_KEY', default='')

OPEN_XR_API_KEY = config('OPEN_XR_API_KEY', default='')

if ENABLE_DEBUG_TOOLBAR:
    INTERNAL_IPS = ['127.0.0.1', ]
    INSTALLED_APPS += ['debug_toolbar', ]
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware', ]

