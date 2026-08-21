FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml alembic.ini ./
COPY apps/api ./apps/api

RUN pip install --no-cache-dir . \
    && addgroup --system --gid 10001 notesolve \
    && adduser --system --uid 10001 --ingroup notesolve notesolve \
    && mkdir -p /data /vault \
    && chown -R notesolve:notesolve /app /data /vault

USER notesolve

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn notesolve.main:app --app-dir apps/api --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
