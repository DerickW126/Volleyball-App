from celery import shared_task
from django.apps import apps
from .utils import send_notification
import datetime
from datetime import timedelta
from volleyball_app.celery import app as celery_app
from django.apps import apps
from django.utils import timezone
from django.db import models
from django.contrib.auth import get_user_model

def schedule_event_status_updates(event, is_overnight=False):
    ScheduledReminder = apps.get_model('notifications', 'ScheduledReminder')
    now = timezone.now()

    event_start_datetime = timezone.make_aware(
        datetime.datetime.combine(event.date, event.start_time)
    )

    if event.status == 'canceled':
        return
        
    # Adjust the end date for overnight events
    end_date = event.date + timedelta(days=1) if is_overnight else event.date

    event_end_datetime = timezone.make_aware(
        datetime.datetime.combine(end_date, event.end_time)
    )

    if now >= event_end_datetime:
        event.status = 'past'
        event.save()
    elif now >= event_start_datetime:
        event.status = 'playing'
        event.save()

        task_past = set_event_status.apply_async((event.id, 'past'), eta=event_end_datetime)
        ScheduledReminder.objects.create(event_id=event.id, task_id=task_past.id)
    else:
        event.status = 'open'
        event.save()

        task_playing = set_event_status.apply_async((event.id, 'playing'), eta=event_start_datetime)
        task_past = set_event_status.apply_async((event.id, 'past'), eta=event_end_datetime)

        ScheduledReminder.objects.create(event_id=event.id, task_id=task_playing.id)
        ScheduledReminder.objects.create(event_id=event.id, task_id=task_past.id)

def schedule_reminders(event, is_overnight=False):
    ScheduledReminder = apps.get_model('notifications', 'ScheduledReminder')

    event_start_datetime = timezone.make_aware(
        datetime.datetime.combine(event.date, event.start_time)
    )

    # Adjust the reminder times if the event spans multiple days
    if is_overnight:
        print(f"Scheduling reminders for overnight event: {event.name}")

    reminder_times = {
        " 再 24 小時": timedelta(hours=24),
        " 再 1 小時": timedelta(hours=1),
        " 再 30 分鐘": timedelta(minutes=30),
        "": timedelta(seconds=0)
    }

    current_time = timezone.now()

    for label, delta in reminder_times.items():
        reminder_time = event_start_datetime - delta

        if reminder_time >= current_time:
            result = celery_app.send_task(
                'notifications.tasks.remind_users_before_event',
                args=[event.id, label],
                eta=reminder_time,
            )
            ScheduledReminder.objects.create(event_id=event.id, task_id=result.id)
        else:
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
        if event.status == 'canceled':
            return

        now = timezone.now()

        # Calculate event's start and end datetime
        event_start_datetime = timezone.make_aware(
            datetime.datetime.combine(event.date, event.start_time)
        )
        end_date = event.date + timedelta(days=1) if event.is_overnight else event.date
        event_end_datetime = timezone.make_aware(
            datetime.datetime.combine(end_date, event.end_time)
        )

        # Add leeway (±10 seconds)
        leeway = timedelta(seconds=10)

        # Check if the current time is within the leeway range
        if status == 'playing' and not (event_start_datetime - leeway <= now <= event_start_datetime + leeway):
            print(f"Skipping status update to 'playing' for Event ID {event_id} due to time mismatch.")
            return
        if status == 'past' and not (event_end_datetime - leeway <= now <= event_end_datetime + leeway):
            print(f"Skipping status update to 'past' for Event ID {event_id} due to time mismatch.")
            return

        # Update status if the timing is valid
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

        if event.status == 'canceled':
            print(f'Event {event_id} is canceled. No notifications will be sent.')
            return
        # Fetch the registrations
        registrations = Registration.objects.filter(event=event, is_approved=True)
        # Notify the event creator
        notify_user_about_event(event.created_by, event_id, f'{event.name} {timedelta_before_event} 就要開始了!')
        notification = Notification.objects.create(
            user=event.created_by,
            title='活動提醒',
            message=f'{event.name}{timedelta_before_event} 就要開始了!',
            event_id=event_id
        )
        # Notify other users
        for registration in registrations:
            user = registration.user
            notification = Notification.objects.create(
                user=user,
                title='活動提醒',
                message=f'{event.name}{timedelta_before_event} 就要開始了!',
                event_id=event_id
            )
            notify_user_about_event(user, event_id, f'{event.name}{timedelta_before_event} 就要開始了!')
            print(f'Notifying user {user.id} about event {event_id}')
    
    except Event.DoesNotExist:
        print(f'Event with id {event_id} does not exist.')

def notify_user_about_event(user, event_id, message):
    # Create the notification
    send_notification(user, "活動提醒", message) 

CustomUser = get_user_model()

@shared_task
def broadcast_new_event_notification_in_chunks(event_id, chunk_size=300):
    """
    Sends a notification about a newly created event to ALL users
    in CHUNKS to avoid performance issues with very large queries.
    """
    # Dynamically load the models to avoid circular imports
    Event = apps.get_model('events', 'Event')
    Notification = apps.get_model('notifications', 'Notification')

    # 1. Fetch the event
    try:
        event = Event.objects.get(pk=event_id)
    except Event.DoesNotExist:
        print(f"Event with id {event_id} does not exist.")
        return

    # 2. Prepare the notification content
    title_msg = "新活動創立通知"
    body_msg = f"活動 '{event.name}' 已創建，快來看看吧！"

    # 3. Get all users (or filter if you only want a subset)
    all_users = CustomUser.objects.exclude(pk=event.created_by_id)
    total_users = all_users.count()

    offset = 0
    notified_count = 0

    # 4. Iterate over users in slices of 'chunk_size'
    while offset < total_users:
        chunk = all_users[offset : offset + chunk_size]
        for user in chunk:
            send_notification(user, title_msg, body_msg)
            notified_count += 1
            print(user.nickname)

        offset += chunk_size

    print(
        f"Broadcasted event '{event.name}' notification "
        f"to {notified_count} users out of {total_users} total."
    )