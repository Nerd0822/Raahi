FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY Backend/pyproject.toml Backend/uv.lock ./
RUN uv sync --frozen --no-dev

COPY Backend/ .

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
