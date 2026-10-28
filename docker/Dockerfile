# syntax=docker/dockerfile:1

# Build the single-page frontend once; the nginx stage below copies its output.
FROM node:22-alpine AS frontend

WORKDIR /app

COPY Frontend/package.json Frontend/package-lock.json ./
RUN npm ci

COPY Frontend/ .
RUN npm run build


# Django API server. Compose builds this target as the `backend` service.
FROM python:3.14-slim AS backend

COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY Backend/pyproject.toml Backend/uv.lock ./
RUN uv sync --frozen --no-dev

COPY Backend/ .
COPY docker/entrypoint.sh /app/docker-entrypoint.sh

RUN mkdir -p /app/staticfiles /app/media \
    && useradd --create-home --uid 1000 app \
    && chown -R app:app /app \
    && chmod +x /app/docker-entrypoint.sh

ENV PATH="/app/.venv/bin:$PATH"

USER app
EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "home.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "240", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]


# Static frontend + reverse proxy. Compose builds this target as `nginx`.
FROM nginx:1.27-alpine AS web

COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=frontend /app/dist /usr/share/nginx/html

EXPOSE 80
