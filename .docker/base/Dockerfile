FROM ghcr.io/amlglobal/aml_base_image:3.11

ENV OPENBLAS_NUM_THREADS=4

LABEL org.opencontainers.image.source="https://github.com/amlglobal/aml-admin"

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi --no-root \
    && pip install lockfile

