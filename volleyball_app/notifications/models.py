# Create your models here.
# notifications/models.py
from django.db import models
from django.contrib.auth.models import User
from events.models import Event
from push_notifications.models import APNSDevice, GCMDevice
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import datetime, timedelta
from celery import current_app as celery_app
from django.utils.timezone import make_aware, get_current_timezone
from .tasks import remind_users_before_event#, cancel_old_notifications
from celery.worker.control import revoke
from django.conf import settings

class ScheduledReminder(models.Model):
    event_id = models.IntegerField(null=True)
    task_id = models.CharField(max_length=255)  # Store the Celery task ID
    #scheduled_time = models.DateTimeField()  # When the notification is supposed to be sent
    #created_at = models.DateTimeField(auto_now_add=True)  # When the notification was scheduled
    updated_at = models.DateTimeField(auto_now=True)  # Last time the record was updated

    def __str__(self):
        return f"Notification for event {self.event.id} scheduled at {self.scheduled_time}"


class CustomFCMDevice(GCMDevice):
    custom_user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    event_id = models.IntegerField(null=True)
    title = task_id = models.CharField(max_length=255, null=True, blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    #is_celery_task = models.BooleanField(default=False)  # New field
    task_id = models.CharField(max_length=255, null=True, blank=True)  # To store Celery task ID if applicable

    def __str__(self):
        return f"Notification for {self.user.username} - {self.message}"

