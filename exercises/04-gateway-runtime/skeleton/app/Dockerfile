# syntax=docker/dockerfile:1
FROM php:8.3-fpm-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libfcgi-bin \
    && rm -rf /var/lib/apt/lists/*

COPY www.conf /usr/local/etc/php-fpm.d/www.conf
WORKDIR /var/www/html
EXPOSE 9000
CMD ["php-fpm", "-F"]
