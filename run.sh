#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Run database migrations
echo "Applying database migrations..."
python manage.py migrate

# Start Gunicorn web server in the background
echo "Starting Gunicorn..."
gunicorn core.wsgi &

# Start Celery worker
echo "Starting Celery worker..."
celery -A core worker -l info