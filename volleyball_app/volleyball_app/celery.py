from __future__ import absolute_import, unicode_literals
import os
from celery.schedules import crontab
from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'volleyball_app.settings')

app = Celery('volleyball_app')

app.conf.beat_schedule = {
    'schedule-notifications-every-minute': {
        'task': 'volleyball_app.tasks.schedule_notifications',
        'schedule': crontab(minute='*/1'),  # Run every minute
    },
}

# Using a string here means the worker does not have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()
