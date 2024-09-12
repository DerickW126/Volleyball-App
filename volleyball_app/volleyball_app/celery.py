# myproject/celery.py
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab
# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'volleyball_app.settings')

app = Celery('volleyball_app')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


app.conf.beat_schedule = {
    'remind-users-before-event': {
        'task': 'events.tasks.remind_users_before_event',
        'schedule': crontab(hour=0, minute=0),  # Runs daily at midnight
        'args': (1,),  # Provide a dummy event_id or adjust to dynamically pass IDs
    },
}