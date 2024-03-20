
### Virtual Environment
You need to use Poetry to manage virtual environment
**Create new virtual environment**

```shell
poetry env use python3.11  # Create virtualenv
portry shell  # Activate virtualenv in current shell
poetry install  # Install dependencies
```

**Example of `.env` file for local development (parsed by poetry env automatically)**

```dotenv
DOMAIN="ops-portal.local"
AML_DOD_PORTAL_DOMAIN="dod-portal.local"
DEBUG=1
# Enable Django Debug Toolbar
ENABLE_DEBUG_TOOLBAR=0
# Enable background scheduler tasks execution (Celery cron)
BACKGROUND_SCHEDULER=1

# K/V (Redis, KeyDB) settings
REDIS_HOST=localhost
#REDIS_PORT=6301
#REDIS_PASS=redis_password

# Primary Postgres Database settings
#DB_HOST="localhost"
DB_PORT=5432
DB_NAME=aml_v2_dev
DB_USER=aml_v2_dev
#DB_PASS=db_pass

# AWS S3 Storage settings
#AWS_ACCESS_KEY_ID=
#AWS_SECRET_ACCESS_KEY=
#AWS_STORAGE_BUCKET_NAME=
#AWS_S3_REGION_NAME=

# SMTP settings
#EMAIL_HOST='sandbox.smtp.mailtrap.io'
#EMAIL_HOST_USER=
#EMAIL_HOST_PASSWORD=
#EMAIL_PORT=

SOLO_CACHE='off'

# Twillio (WhatsApp messaging) settings
#TWILIO_ACCOUNT_SID=
#TWILIO_AUTH_TOKEN=
#TWILIO_SENDER_NUMBER=

# Google Firebase key (fcm.json) base64 encoded
#FIREBASE_KEY_B64=
# FIREBASE_API_KEY=

# what3words API Key
#WHAT3WORDS_API_KEY=

# Google Maps
#GOOGLE_MAPS_API_KEY=

# OFAC API
#OFAC_API_KEY=
```

### Ops Portal
**Main Application**
```shell
DEBUG=1 python manage.py runserver 127.0.0.1:7007
```
**Jupyter Notebook**
```shell
DJANGO_SETTINGS_MODULE=app.settings_dev python manage.py shell_plus --notebook
```
### DoD application
**Main Application**
```shell
DEBUG=1 python manage.py runserver 127.0.0.1:7009 --settings app.settings_dod
```
**Jupyter Notebook**
```shell
DJANGO_SETTINGS_MODULE=app.settings_dev_dod python manage.py shell_plus --notebook
```
