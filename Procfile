web: daphne -b 0.0.0.0 -p $PORT volleyball_app.asgi:application
worker: celery -A volleyball_app.celery worker --loglevel=info