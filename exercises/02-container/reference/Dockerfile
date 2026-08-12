# syntax=docker/dockerfile:1
# [Implementation 2] 고정 runtime과 listen 환경으로 실행 기반을 선언합니다.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=8080

# [Implementation 3] server artifact를 비특권 계정 소유로 image에 복사합니다.
WORKDIR /app
COPY --chown=65532:65532 app/server.py /app/server.py

# [Implementation 4] process identity와 공개 port, PID 1 entrypoint를 한 경계로 닫습니다.
USER 65532:65532
EXPOSE 8080
ENTRYPOINT ["python", "/app/server.py"]
