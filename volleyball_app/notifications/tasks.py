from celery import shared_task
from django.apps import apps
from .utils import send_notification

@shared_task
def remind_users_before_event(event_id):
    # Dynamically get models
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
        notify_user_about_event(event.created_by, event_id, 'Your event is starting soon!')
        notification = Notification.objects.create(
            user=event.created_by,
            message='Your event is starting soon!',
            event_id=event_id
        )
        # Notify other users
        for registration in registrations:
            user = registration.user
            notification = Notification.objects.create(
                user=user,
                message='Your event is starting soon!',
                event_id=event_id
            )
            notify_user_about_event(user, event_id, 'Your event is starting soon!')
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