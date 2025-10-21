#!/bin/sh
set -o errexit  # Exit immediately on error
set -o pipefail
set -o nounset

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Applying database migrations..."
python manage.py migrate --noinput

# Optional: generate API schema only in debug/dev
# if [ "${DJANGO_DEBUG:-False}" = "True" ]; then
#   python manage.py spectacular --color --file schema.yml
# fi

echo "Starting Gunicorn with UvicornWorker..."
exec /usr/local/bin/gunicorn config.asgi \
    --bind 0.0.0.0:5000 \
    --chdir=/app \
    -k uvicorn.workers.UvicornWorker \
    --workers 4 \
    --threads 2 \
    --timeout 120
