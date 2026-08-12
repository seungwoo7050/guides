# syntax=docker/dockerfile:1
FROM nginx:stable-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        openssl \
    && rm -rf /var/lib/apt/lists/*

# [Implementation 6] 검증된 template과 certificate lifecycle entrypoint를 image에 넣습니다.
COPY default.conf.template /etc/nginx/templates/default.conf.template
COPY docker-entrypoint.sh /usr/local/bin/exercise-entrypoint.sh
RUN chmod 0755 /usr/local/bin/exercise-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/exercise-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
