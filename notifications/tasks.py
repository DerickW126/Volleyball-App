from celery import shared_task
from django.apps import apps
from .utils import send_notification
#from celery.worker.control import revoke
import datetime
from datetime import timedelta
from volleyball_app.celery import app as celery_app
from django.apps import apps
from django.utils import timezone
from django.db import models

def schedule_event_status_updates(event):
    now = timezone.now()
    
    event_start_datetime = timezone.make_aware(
        datetime.datetime.combine(event.date, event.start_time)
    )
    event_end_datetime = timezone.make_aware(
        datetime.datetime.combine(event.date, event.end_time)
    )
    
    if now >= event_end_datetime:
        task = set_event_status.apply_async((event.id, 'past'), eta=now + timedelta(seconds=5))
        ScheduleReminder.objects.create(event=event, task_id=task.id, status='past')

    elif now > event_start_datetime:
        task = set_event_status.apply_async((event.id, 'playing'), eta=now + timedelta(seconds=5))
        ScheduleReminder.objects.create(event=event, task_id=task.id, status='playing')

    else:
        task_open = set_event_status.apply_async((event.id, 'open'), eta=now + timedelta(seconds=5))
        ScheduleReminder.objects.create(event=event, task_id=task_open.id, status='open')

        task_playing = set_event_status.apply_async((event.id, 'playing'), eta=event_start_datetime)
        ScheduleReminder.objects.create(event=event, task_id=task_playing.id, status='playing')

        task_past = set_event_status.apply_async((event.id, 'past'), eta=event_end_datetime)
        ScheduleReminder.objects.create(event=event, task_id=task_past.id, status='past')

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

    for label, delta in reminder_times.items():
        reminder_time = event_start_datetime - delta
        result = celery_app.send_task(
            'notifications.tasks.remind_users_before_event',
            args=[event.id, label],
            eta=reminder_time,
        )
        
        ScheduledReminder.objects.create(
            #user=event.created_by,
            event_id=event.id,
            #title='活動時間提醒',
            #message=f'提醒: {label} before event starts!',
            #is_celery_task=True,
            task_id=result.id
        )

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
                message=f'{event.name} 再 {timedelta_before_event} 就要開始了!',
                event_id=event_id
            )
            notify_user_about_event(user, event_id, f'{event.name} 再 {timedelta_before_event} 就要開始了!')
            print(f'Notifying user {user.id} about event {event_id}')
    
    except Event.DoesNotExist:
        print(f'Event with id {event_id} does not exist.')

def notify_user_about_event(user, event_id, message):
    # Create the notification
    '''
    Notification = apps.get_model('notifications', 'Notification')
    
    # Create the notification record
    notification = Notification.objects.create(
        user=user,
        message=message,
        event_id=event_id
    )
    '''
    # Send notification (using a utility function)
    send_notification(user, "新的通知", message)