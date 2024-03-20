from .settings import *

SITE_ID = 2

ALLOWED_HOSTS = ['localhost', '127.0.0.1',
                 config('AML_DOD_PORTAL_DOMAIN', default='localhost')]

# Generate CSRF_TRUSTED_ORIGINS from the ALLOWED_HOSTS
CSRF_TRUSTED_ORIGINS = []
for hostname in ALLOWED_HOSTS:
    CSRF_TRUSTED_ORIGINS.append(f'http://{hostname}')
    CSRF_TRUSTED_ORIGINS.append(f'https://{hostname}')

ROOT_URLCONF = 'app.urls_dod'
SESSION_COOKIE_NAME = 'aml_dod_session'
LOGIN_URL = 'dod:login'
LOGIN_REDIRECT_URL = 'dod:index'
LOGOUT_REDIRECT_URL = 'dod:login'

# INSTALLED_APPS += [
#     'dod_portal',
# ]

AUTHENTICATION_BACKENDS = [
    'dod_portal.backends.DodUserBackend',
]

MIDDLEWARE += [
    'dod_portal.middlewares.DodPersonMiddleware'
]
