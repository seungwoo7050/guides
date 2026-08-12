# syntax=docker/dockerfile:1
FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        mariadb-client \
        mariadb-server \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/lib/mysql/* \
    && install -d -m 0755 -o mysql -g mysql /run/mysqld /var/lib/mysql

# [Implementation 7] 완성된 server contract와 entrypoint를 image runtime 경계에 조립합니다.
COPY 50-server.cnf /etc/mysql/mariadb.conf.d/50-server.cnf
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod 0755 /usr/local/bin/docker-entrypoint.sh

EXPOSE 3306
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["mariadbd", "--user=mysql", "--console"]
