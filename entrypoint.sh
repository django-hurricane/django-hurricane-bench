#!/usr/bin/env bash
set -e

cd /app/src

echo "[entrypoint] Checking PostgreSQL connection..."
python << 'EOF'
import os
import socket
import sys
import time

host = os.environ.get("DB_HOST", "postgres")
port = int(os.environ.get("DB_PORT", "5432"))
start = time.time()
while time.time() - start < 60:
    try:
        with socket.create_connection((host, port), timeout=2):
            print(f"[entrypoint] Successfully connected to PostgreSQL at {host}:{port}")
            sys.exit(0)
    except OSError:
        time.sleep(1)

print(f"[entrypoint] ERROR: Timeout waiting for PostgreSQL at {host}:{port}")
sys.exit(1)
EOF

echo "[entrypoint] Applying database migrations..."
python manage.py migrate --noinput

echo "[entrypoint] Seeding benchmark database..."
python manage.py seed_db

echo "[entrypoint] Starting Django Hurricane..."
exec "$@"
