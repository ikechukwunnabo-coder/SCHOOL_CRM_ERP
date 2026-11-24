#!/bin/sh
set -e

if [ "${1:-}" = "celery" ]; then
    exec "$@"
fi

attempt=0
until python manage.py migrate --noinput; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 30 ]; then
        echo "Database migration failed after 30 attempts"
        exit 1
    fi
    sleep 2
done

python manage.py collectstatic --noinput

exec "$@"
