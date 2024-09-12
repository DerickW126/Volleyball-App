# Create your models here.
# notifications/models.py
from django.db import models
from django.contrib.auth.models import User
from events.models import Event
from push_notifications.models import APNSDevice, GCMDevice
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from celery import current_app as celery_app
from .tasks import remind_users_before_event

@receiver(post_save, sender=Event)
def schedule_event_reminder(sender, instance, **kwargs):
    if kwargs.get('created', False):
        # Combine the event date and start time to get a datetime object
        event_date = instance.date
        event_start_time = instance.start_time
        event_datetime = datetime.combine(event_date, event_start_time)

        # Convert to timezone-aware datetime if necessary
        event_datetime = make_aware(event_datetime)

        # Calculate the reminder time
        reminder_time = event_datetime - timedelta(hours=24)

        # Schedule the task
        if reminder_time > datetime.now():  # Ensure reminder_time is in the future
            # Use the Celery app instance for sending the task
            from celery import current_app as celery_app
            celery_app.send_task(
                'events.tasks.remind_users_before_event',
                args=[instance.id],
                eta=reminder_time,
            )

class CustomFCMDevice(GCMDevice):
    custom_user = models.OneToOneField('auth.User', on_delete=models.CASCADE)

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event_id = models.IntegerField(null=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.username} - {self.message}"
