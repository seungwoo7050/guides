# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 APP_HOST=0.0.0.0 APP_PORT=8080
WORKDIR /app
COPY server.py healthcheck.py /app/
RUN mkdir -p /data \
    && chown -R 65532:65532 /app /data
USER 65532:65532
EXPOSE 8080
ENTRYPOINT ["python", "/app/server.py"]
