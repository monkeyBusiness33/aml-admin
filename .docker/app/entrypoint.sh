#!/bin/bash
set -e


if [ -n "$FIREBASE_KEY_B64" ]; then
    echo $FIREBASE_KEY_B64 | base64 -d > fcm.json
fi

# Collect static files
python manage.py collectstatic --noinput

# Wait until databases is ready
/wait

if [[ "$HOSTNAME" == "ads-dev-aml-app" || "$HOSTNAME" == "vh1-dh1-aml-app" ]]; then

    if [ -n "$STATIC_CDN" ]; then
      echo "Upload static content to Cloudflare R2"
      AWS_ACCESS_KEY_ID=$STATIC_CDN_ACCESS_KEY_ID \
      AWS_SECRET_ACCESS_KEY=$STATIC_CDN_SECRET_ACCESS_KEY \
      aws --endpoint-url="${STATIC_CDN_ENDPOINT_URL}" s3 sync staticfiles/ s3://"$STATIC_CDN_STORAGE_BUCKET_NAME"/
    fi

    echo "Migrations for 'default' database..."
    python manage.py migrate --database=default

    echo "Writing fixtures"
    python manage.py loaddata */fixtures/*.yaml
fi

# echo "Starting Celery worker..."
celery -A app worker -l INFO -Q "$(hostname -s)"_queue &
celery -A app beat -l INFO &
DJANGO_SETTINGS_MODULE=app.settings_dod daphne -b 0.0.0.0 -p 8001 app.asgi_dod:application &
exec "$@"
