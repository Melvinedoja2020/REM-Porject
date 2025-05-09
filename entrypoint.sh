#!/bin/sh

# Ensure static files are collected before running the app
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Generate API schema if needed (for DRF Spectacular)
echo "Generating API schema..."
python manage.py spectacular --color --file schema.yml

# Run database migrations
echo "Running database migrations..."
python manage.py migrate

# Finally, start the application
echo "Starting application..."
exec python manage.py runserver 0.0.0.0:5000
# exec daphne -b 0.0.0.0 -p 8000 --ws-protocol "graphql-ws" --proxy-headers my_project.asgi:channel_layer
# exec python manage.py runworker --only-channels=http.* --only-channels=websocket.*
# exec daphne -b 0.0.0.0 -p 5000  --proxy-headers config.asgi:application
# exec daphne -b 0.0.0.0 -p 5000 config.asgi:application