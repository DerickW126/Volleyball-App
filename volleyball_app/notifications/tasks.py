from celery import shared_task
from django.apps import apps
from .utils import send_notification
def notify_user_about_event(user, event_id, message):
    # Create the notification
    notification = Notification.objects.create(
        user=user,
        message=message,
        event_id=event_id
    )
    send_notification(user, "新的通知", message)
    
@shared_task
def remind_users_before_event(event_id):
    Event = apps.get_model('events', 'Event')
    Registration = apps.get_model('events', 'Registration')
    
    # Fetch event and registrations
    event = Event.objects.get(id=event_id)
    registrations = Registration.objects.filter(event=event, is_approved=True)
    
    # Notify users
    for registration in registrations:
        user = registration.user
        # Your notification logic here
        notify_user_about_event(user, event_id, '快開打了')
        print(f'Notifying user {user.id} about event {event_id}')