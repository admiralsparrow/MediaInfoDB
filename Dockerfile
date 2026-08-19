# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app
COPY VERSION /VERSION
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Final image
FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl ca-certificates gnupg gosu \
    && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/pgdg.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/pgdg.gpg] http://apt.postgresql.org/pub/repos/apt $(. /etc/os-release && echo "$VERSION_CODENAME")-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        libmediainfo0v5 \
        nginx \
        postgresql-16 \
        postgresql-client-16 \
        sudo \
        locales \
    && sed -i '/en_US.UTF-8/s/^# //' /etc/locale.gen \
    && locale-gen \
    && rm -rf /var/lib/apt/lists/*

# Create non-root app user and configure nginx to run as appuser
RUN useradd -r -s /bin/false appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app && \
    chown -R appuser:appuser /usr/share/nginx/html && \
    mkdir -p /var/log/nginx /var/lib/nginx /run /tmp/nginx && \
    chown -R appuser:appuser /var/log/nginx /var/lib/nginx /run /tmp/nginx && \
    sed -i '/^user /d' /etc/nginx/nginx.conf && \
    sed -i 's|^pid .*|pid /tmp/nginx/nginx.pid;|' /etc/nginx/nginx.conf

# Backend
WORKDIR /app
ENV PYTHONPATH=/app

COPY VERSION .
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
RUN chmod +x start.sh

# Frontend
COPY --from=frontend-build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
RUN rm -f /etc/nginx/sites-enabled/default

# PostgreSQL data and runtime directories
RUN mkdir -p /var/lib/postgresql/data /var/run/postgresql && \
    chown -R postgres:postgres /var/lib/postgresql/data /var/run/postgresql

EXPOSE 3745

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Entrypoint runs as root only for PG init, then drops to appuser for nginx+app
USER root
CMD ["/entrypoint.sh"]
