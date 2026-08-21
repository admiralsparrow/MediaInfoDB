#!/bin/bash
set -e

DB_NAME="${POSTGRES_DB:-mediainfodb}"
DB_USER="${POSTGRES_USER:-mediainfodb}"
DB_PASSWORD="${DB_PASSWORD:-mediainfo_dev}"

# If DATABASE_URL is not set, start the internal PostgreSQL
if [ -z "$DATABASE_URL" ]; then
    echo "Starting internal PostgreSQL..."

    # Fix ownership and permissions on mounted volume
    chown -R postgres:postgres /var/lib/postgresql/data
    chmod 700 /var/lib/postgresql/data

    # Ensure PostgreSQL runtime directory exists with correct permissions
    mkdir -p /var/run/postgresql
    chown postgres:postgres /var/run/postgresql

    # Initialize database if needed
    if [ ! -f /var/lib/postgresql/data/PG_VERSION ]; then
        echo "Initializing PostgreSQL data directory..."
        sudo -u postgres /usr/lib/postgresql/*/bin/initdb \
            -D /var/lib/postgresql/data \
            --username="$DB_USER" \
            --auth-local=trust \
            --auth-host=scram-sha-256
        # Configure to listen on localhost only
        echo "listen_addresses = 'localhost'" >> /var/lib/postgresql/data/postgresql.conf
        echo "host all all 127.0.0.1/32 scram-sha-256" >> /var/lib/postgresql/data/pg_hba.conf
    fi

    # Remove stale pid file only if no PostgreSQL process is running
    if [ -f /var/lib/postgresql/data/postmaster.pid ] && ! pgrep -f "postgres.*-D /var/lib/postgresql/data" > /dev/null; then
        rm -f /var/lib/postgresql/data/postmaster.pid
    fi

    # Start PostgreSQL
    sudo -u postgres /usr/lib/postgresql/*/bin/pg_ctl \
        -D /var/lib/postgresql/data \
        -l /var/lib/postgresql/data/logfile \
        start || { echo "PostgreSQL failed to start. Log:"; cat /var/lib/postgresql/data/logfile; exit 1; }

    # Wait for PostgreSQL to be ready
    until pg_isready -q; do
        sleep 0.5
    done

    # Create database if it doesn't exist (user is the superuser from initdb)
    # Connect to 'postgres' db explicitly — the app db may not exist yet on fresh clusters
    sudo -u postgres psql -U "$DB_USER" -d postgres -tc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1 || \
        sudo -u postgres psql -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

    # Set/update password using escaped value to avoid injection
    ESCAPED_PW=$(printf '%s' "$DB_PASSWORD" | sed "s/'/''/g")
    sudo -u postgres psql -U "$DB_USER" -d postgres -c "ALTER USER $DB_USER WITH PASSWORD '${ESCAPED_PW}';"

    URL_ENCODED_PW=$(printf '%s' "$DB_PASSWORD" | python3 -c "import sys, urllib.parse; print(urllib.parse.quote(sys.stdin.read(), safe=''))")
    export DATABASE_URL="postgresql+asyncpg://${DB_USER}:${URL_ENCODED_PW}@localhost:5432/${DB_NAME}"
    echo "Internal PostgreSQL ready."
else
    echo "Using external database: $DATABASE_URL"
fi

# Trap signals to cleanly stop child processes
cleanup() {
    echo "Shutting down..."
    nginx -s quit 2>/dev/null
    kill "$BACKEND_PID" 2>/dev/null
    wait "$BACKEND_PID" 2>/dev/null
    exit 0
}
trap cleanup SIGTERM SIGINT SIGQUIT

# Drop to appuser for nginx and backend
# Start nginx as appuser (listens on 3745, no privileged port)
gosu appuser nginx -g "daemon off;" &
NGINX_PID=$!

# Monitor nginx and restart if it crashes
(
    while true; do
        wait "$NGINX_PID" 2>/dev/null
        if [ $? -ne 0 ] && kill -0 $$ 2>/dev/null; then
            echo "nginx exited unexpectedly, restarting..."
            sleep 1
            gosu appuser nginx -g "daemon off;" &
            NGINX_PID=$!
        else
            break
        fi
    done
) &

# Start backend as appuser
cd /app
gosu appuser ./start.sh &
BACKEND_PID=$!
wait "$BACKEND_PID"
