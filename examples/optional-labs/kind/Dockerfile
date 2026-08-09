FROM python:3.12.11-alpine3.22

WORKDIR /app
COPY server.py /app/server.py
USER 65532:65532
EXPOSE 8080
ENTRYPOINT ["python3", "/app/server.py"]
