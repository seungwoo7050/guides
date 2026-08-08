# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=8080

WORKDIR /app
COPY --chown=65532:65532 app/server.py /app/server.py

USER 65532:65532
EXPOSE 8080
ENTRYPOINT ["python", "/app/server.py"]
