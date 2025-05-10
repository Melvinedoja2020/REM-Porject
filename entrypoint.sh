# #!/bin/sh

# # Your series of commands
# python manage.py collectstatic --noinput --clear
# # python manage.py spectacular --color --file schema.yml
# python manage.py migrate
# # exec /usr/local/bin/gunicorn config.asgi --bind 0.0.0.0:5000 --chdir=/app -k uvicorn.workers.UvicornWorker
# # exec python manage.py startpublishing
# exec python manage.py runserver 0.0.0.0:5000
# # exec daphne -b 0.0.0.0 -p 8000 --ws-protocol "graphql-ws" --proxy-headers my_project.asgi:channel_layer
# # exec python manage.py runworker --only-channels=http.* --only-channels=websocket.*
# # exec daphne -b 0.0.0.0 -p 5000  --proxy-headers config.asgi:application
# # exec daphne -b 0.0.0.0 -p 5000 config.asgi:application


#!/bin/sh

# Exit immediately if a command exits with a non-zero status
set -e

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Start Gunicorn server
echo "Starting Gunicorn..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:5000 \
    --workers 3 \
    --threads 2 \
    --timeout 120

