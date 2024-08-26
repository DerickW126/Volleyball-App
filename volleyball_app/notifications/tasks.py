from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from notifications.utils import send_notification
import events.models

@shared_task
def notify_event_users(event_id, time_before):
    try:
        event = events.models.Event.objects.get(id=event_id)
        start_time = timezone.make_aware(
            timezone.datetime.combine(event.date, event.start_time) - timedelta(minutes=time_before)
        )
        now = timezone.now()
        
        if now >= start_time:
            users = User.objects.filter(event_registrations__event=event)
            for user in users:
                send_notification(user, event)
    except Event.DoesNotExist:
        pass

@shared_task
def schedule_notifications(event_id):
    # Fetch events starting within the next 24 hours, 1 hour, and 10 minutes
    upcoming_events = Event.objects.filter(start_time__gte=now, start_time__lte=now + timedelta(days=1))
    
    for event in upcoming_events:
        event_time = timezone.make_aware(
            timezone.datetime.combine(event.date, event.start_time)
        )
        
        # Schedule notification tasks
        if event_time - timedelta(hours=24) > now:
            notify_event_users.apply_async(args=[event.id, 1440], eta=event_time - timedelta(hours=24))
        if event_time - timedelta(hours=1) > now:
            notify_event_users.apply_async(args=[event.id, 60], eta=event_time - timedelta(hours=1))
        if event_time - timedelta(minutes=10) > now:
            notify_event_users.apply_async(args=[event.id, 10], eta=event_time - timedelta(minutes=10))
