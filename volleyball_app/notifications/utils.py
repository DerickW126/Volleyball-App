# notifications/utils.py
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification
from .serializers import NotificationSerializer

def notify_user_about_event(user, event_id, message):
    # Create the notification
    notification = Notification.objects.create(
        user=user,
        message=message,
        event_id=event_id
    )

    # Send the notification via WebSocket
    serialized_notification = NotificationSerializer(notification).data
    channel_layer = get_channel_layer()
    print(user, message, event_id)
    async_to_sync(channel_layer.group_send)(
        f'notifications_{user.id}',
        {
            'type': 'send_notification',
            'notification': serialized_notification,
        }
    )