
# Étape de construction : uv et son cache de téléchargement (~170 Mo) ne sont pas dans l'image finale.
FROM python:3.12-slim AS build

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --no-cache

FROM python:3.12-slim

ARG APP_VERSION=dev
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    APP_VERSION=$APP_VERSION

WORKDIR /app

COPY --from=build /opt/venv /opt/venv
COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app

# /data et /backups appartiennent à app : un volume nommé neuf en hérite (sinon il serait à root).
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /data /backups \
    && chown app:app /data /backups
USER app

EXPOSE 8000

# Les migrations sont appliquées à chaque démarrage (SPEC §34).
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn --factory app.main:create_app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
