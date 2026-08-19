# syntax=docker/dockerfile:1
# [Implementation 5] Non-root runtime image
FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=8080
WORKDIR /app
COPY server.py healthcheck.py /app/
RUN install -d -m 0750 -o 65532 -g 65532 /data \
    && chown -R 65532:65532 /app
USER 65532:65532
EXPOSE 8080
ENTRYPOINT ["python", "/app/server.py"]
