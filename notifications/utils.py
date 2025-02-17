# notifications/utils.py
from fcm_django.models import FCMDevice
from firebase_admin.messaging import Message, Notification
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from firebase_admin import messaging, _messaging_utils


def send_notification(user, title_msg, body_msg):
    # Retrieve the FCMDevice for the user
    device = FCMDevice.objects.filter(user=user).first()

    if device:
        try:
            result = device.send_message(
                Message(notification=Notification(title=title_msg, body=body_msg))
            )
            print(result)
            return {'status': 'success', 'result': result}
        except _messaging_utils.UnregisteredError:
            # Handle unregistered token
            device.delete()
            print(f"[ERROR] Unregistered FCM token for user {user.id}, removed from database.")
        except Exception as e:
            print(f"[ERROR] Could not send notification to user {user.id}: {e}")
    else:
        return {'status': 'error', 'message': 'No device found for user'}
        
def send_bulk_notification(registrations, event):
    devices = FCMDevice.objects.filter(user__in=[reg.user for reg in registrations])
    for device in devices:
        body_msg = f"活動 {event.name} 的內容已被更改，請重新確認活動時間，地點，要求等"
        device.send_message(Message(notification=Notification(title="活動資訊更改", body=body_msg)))



