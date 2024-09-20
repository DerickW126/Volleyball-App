web: gunicorn volleyball_app.wsgi --log-file -
worker: celery -A volleyball_app.celery worker --loglevel=info
daphne: daphne -b 0.0.0.0 -p $PORT volleyball_app.asgi:application