# syntax=docker/dockerfile:1.7
# AfyaSync API image. Build context is the repository root:
#   docker build -f api/Dockerfile --target prod .
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"
COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /uvx /bin/
RUN groupadd --system app && useradd --system --gid app --home-dir /app --shell /usr/sbin/nologin app \
    && mkdir -p /app/api /data && chown app:app /data
WORKDIR /app/api

FROM base AS dev
COPY api/pyproject.toml api/uv.lock ./
RUN uv sync --frozen --no-install-project
USER app
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

FROM base AS prod
COPY api/pyproject.toml api/uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev
COPY api/ ./
RUN DJANGO_ENV=test python manage.py collectstatic --noinput >/dev/null
USER app
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60"]
