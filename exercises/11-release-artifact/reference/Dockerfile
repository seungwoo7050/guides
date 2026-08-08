ARG BASE_IMAGE=python:3.14.6-alpine3.24
FROM ${BASE_IMAGE}

ARG VCS_REF
ARG VERSION
ARG BUILD_DATE
LABEL org.opencontainers.image.source="https://github.com/example/notes" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}"

RUN addgroup -S app && adduser -S -G app app
WORKDIR /app
COPY --chown=app:app app.py /app/app.py
USER app
ENTRYPOINT ["python3", "/app/app.py"]
