ARG APP_IMAGE=aml_app
FROM ${APP_IMAGE} as app_image

# Generate staticfiles bundle
RUN python manage.py collectstatic --noinput

FROM nginx:alpine
LABEL org.opencontainers.image.source="https://github.com/amlglobal/aml-admin"

# Copy staticfiles bundle to the image
COPY --from=app_image /app/staticfiles /var/www/static
COPY --from=app_image /app/app/templates/layouts/maintenance_page.html  /var/www/static/maintenance_page.html 
COPY .docker/nginx/nginx.conf /etc/nginx/conf.d/default.conf
