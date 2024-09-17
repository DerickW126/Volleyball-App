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
from .tasks import remind_users_before_event
'''
@receiver(pre_save, sender=Event)
def check_event_time_change(sender, instance, **kwargs):
    if instance.pk:
        # Fetch the existing event instance before saving the new changes
        old_event = Event.objects.get(pk=instance.pk)
        
        # Check if the date or start_time has changed
        if old_event.start_time != instance.start_time or old_event.date != instance.date:
            print("Event time has changed, scheduling new reminders.")
            
            # Calculate the new event start time in UTC
            event_datetime = make_aware(datetime.combine(instance.date, instance.start_time))
            
            # Schedule new notifications for 24 hours before, 1 hour before, and 10 minutes before
            celery_app.send_task(
                'notifications.tasks.remind_users_before_event',
                args=[instance.id, label],
                eta=event_datetime - timedelta(hours=24),
            )
            celery_app.send_task(
                'notifications.tasks.remind_users_before_event',
                args=[instance.id, label],
                eta=event_datetime - timedelta(hours=1),
            )
            celery_app.send_task(
                'notifications.tasks.remind_users_before_event',
                args=[instance.id, label],
                eta=event_datetime - timedelta(minutes=10),
            )
            #remind_users_before_event.apply_async((instance.pk,), eta=event_datetime - timedelta(hours=24))
            #remind_users_before_event.apply_async((instance.pk,), eta=event_datetime - timedelta(hours=1))
            #remind_users_before_event.apply_async((instance.pk,), eta=event_datetime - timedelta(minutes=10))
'''
@receiver(post_save, sender=Event)
def schedule_event_reminder(sender, instance, **kwargs):
    if kwargs.get('created', False):
        # Combine the date and time to create a datetime object
        event_date = instance.date
        event_start_time = instance.start_time
        event_datetime = datetime.combine(event_date, event_start_time)

        # Convert to timezone-aware datetime
        event_datetime = make_aware(event_datetime, get_current_timezone())
        reminder_times = {
            "24 hours": timedelta(hours=24),
            "1 hour": timedelta(hours=1),
            "30 minutes": timedelta(minutes=30),
        }
        
        for label, delta in reminder_times.items():
            reminder_time = event_datetime - delta
            # Schedule the task
            celery_app.send_task(
                'notifications.tasks.remind_users_before_event',
                args=[instance.id],
                eta=reminder_time,
            )
        # Calculate reminder time

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
