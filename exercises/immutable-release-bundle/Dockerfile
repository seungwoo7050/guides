# syntax=docker/dockerfile:1
# [Implementation 2] Immutable image build identity
ARG BASE_IMAGE=python:3.14.0-alpine3.22
FROM ${BASE_IMAGE}
ARG VCS_REF
ARG VERSION
ARG BUILD_DATE
LABEL org.opencontainers.image.source="https://github.com/example/notes" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}"

# [Implementation 3] Non-root runtime ownership
RUN addgroup -S app && adduser -S -G app app
WORKDIR /app
COPY --chown=app:app app.py /app/app.py
USER app
ENTRYPOINT ["python3", "/app/app.py"]
