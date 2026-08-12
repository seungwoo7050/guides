# [Implementation 2] base·source·version·build time을 immutable image identity에 묶습니다.
ARG BASE_IMAGE=python:3.14.6-alpine3.24
FROM ${BASE_IMAGE}

ARG VCS_REF
ARG VERSION
ARG BUILD_DATE
LABEL org.opencontainers.image.source="https://github.com/example/notes" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}"

# [Implementation 3] artifact ownership과 runtime identity를 non-root 계정으로 닫습니다.
RUN addgroup -S app && adduser -S -G app app
WORKDIR /app
COPY --chown=app:app app.py /app/app.py
USER app
ENTRYPOINT ["python3", "/app/app.py"]
