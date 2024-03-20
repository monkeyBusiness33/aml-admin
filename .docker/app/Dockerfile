ARG BRANCH_NAME

FROM ghcr.io/amlglobal/aml_ops_base:$BRANCH_NAME

LABEL org.opencontainers.image.source="https://github.com/amlglobal/aml-admin"

COPY . .

COPY .docker/app/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
EXPOSE 8000 8001
ENTRYPOINT [ "/entrypoint.sh" ]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "app.asgi:application"]
