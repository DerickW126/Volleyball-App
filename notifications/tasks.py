from celery import shared_task
from django.apps import apps
from .utils import send_notification
import datetime
from datetime import timedelta
from volleyball_app.celery import app as celery_app
from django.apps import apps
from django.utils import timezone
from django.db import models

def schedule_event_status_updates(event):
    ScheduledReminder = apps.get_model('notifications', 'ScheduledReminder')
    now = timezone.now()
    
    event_start_datetime = timezone.make_aware(
        datetime.datetime.combine(event.date, event.start_time)
    )
    event_end_datetime = timezone.make_aware(
        datetime.datetime.combine(event.date, event.end_time)
    )

    # If the event has already ended, mark it as 'past'
    if now >= event_end_datetime:
        event.status = 'past'
        event.save()
        # No need to schedule 'past' status since it's already set

    # If the event is ongoing, mark it as 'playing' and schedule 'past' status for when it ends
    elif now >= event_start_datetime:
        event.status = 'playing'
        event.save()

        # Schedule the task to set status to 'past' when the event ends
        task_past = set_event_status.apply_async((event.id, 'past'), eta=event_end_datetime)
        ScheduledReminder.objects.create(event_id=event.id, task_id=task_past.id)
    # If the event is scheduled for the future, mark it as 'open'
    else:
        event.status = 'open'
        event.save()

        # Schedule the task to set status to 'playing' when the event starts
        task_playing = set_event_status.apply_async((event.id, 'playing'), eta=event_start_datetime)
        ScheduledReminder.objects.create(event_id=event.id, task_id=task_playing.id)

        # Schedule the task to set status to 'past' when the event ends
        task_past = set_event_status.apply_async((event.id, 'past'), eta=event_end_datetime)
        ScheduledReminder.objects.create(event_id=event.id, task_id=task_past.id)

def schedule_reminders(event):
    """Schedules reminders for the event."""
    ScheduledReminder = apps.get_model('notifications', 'ScheduledReminder')
    event_start_datetime = timezone.make_aware(
        datetime.datetime.combine(event.date, event.start_time)
    )
    reminder_times = {
        "24 小時": timedelta(hours=24),
        "1 小時": timedelta(hours=1),
        "30 分鐘": timedelta(minutes=30),
    }

    current_time = timezone.now()

    for label, delta in reminder_times.items():
        reminder_time = event_start_datetime - delta

        # Only schedule the reminder if the reminder_time is in the future
        if reminder_time >= current_time:
            result = celery_app.send_task(
                'notifications.tasks.remind_users_before_event',
                args=[event.id, label],
                eta=reminder_time,
            )

            # Create a scheduled reminder entry
            ScheduledReminder.objects.create(
                event_id=event.id,
                task_id=result.id
            )
        else:
            # Optionally, log or track reminders that were skipped because they were in the past
            print(f"Skipping reminder '{label}' for event {event.id} because it is in the past.")

def cancel_old_notifications(event):
    """
    Cancels all old scheduled notifications for the given event.
    """
    ScheduledReminder = apps.get_model('notifications', 'ScheduledReminder')
    reminders = ScheduledReminder.objects.filter(event_id=event.id)

    for reminder in reminders:
        # Revoke the Celery task using its task ID  
        celery_app.control.revoke(reminder.task_id, terminate=True)

        # Delete the reminder record from the database
        reminder.delete()

@shared_task
def set_event_status(event_id, status):
    Event = apps.get_model('events', 'Event')
    try:
        event = Event.objects.get(pk=event_id)
        event.status = status
        event.save()
    except Event.DoesNotExist:
        print(f'Event with id {event_id} does not exist.')

@shared_task
def remind_users_before_event(event_id, timedelta_before_event):

    Event = apps.get_model('events', 'Event')
    Registration = apps.get_model('events', 'Registration')
    Notification = apps.get_model('notifications', 'Notification')
    
    print(f'Reminding users about event {event_id}')
    
    try:
        # Fetch the event
        event = Event.objects.get(id=event_id)
        
        # Fetch the registrations
        registrations = Registration.objects.filter(event=event, is_approved=True)
        # Notify the event creator
        notify_user_about_event(event.created_by, event_id, f'{event.name} 再 {timedelta_before_event} 就要開始了!')
        notification = Notification.objects.create(
            user=event.created_by,
            title='活動提醒',
            message=f'{event.name} 再 {timedelta_before_event} 就要開始了!',
            event_id=event_id
        )
        # Notify other users
        for registration in registrations:
            user = registration.user
            notification = Notification.objects.create(
                user=user,
                title='活動提醒',
                message=f'{event.name} 再 {timedelta_before_event} 就要開始了!',
                event_id=event_id
            )
            notify_user_about_event(user, event_id, f'{event.name} 再 {timedelta_before_event} 就要開始了!')
            print(f'Notifying user {user.id} about event {event_id}')
    
    except Event.DoesNotExist:
        print(f'Event with id {event_id} does not exist.')

def notify_user_about_event(user, event_id, message):
    # Create the notification
    send_notification(user, "活動提醒", message) 