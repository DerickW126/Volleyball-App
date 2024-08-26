# notifications/utils.py
from fcm_django.models import FCMDevice
from firebase_admin.messaging import Message, Notification
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

def send_notification(user, title_msg, body_msg):
    # Retrieve the FCMDevice for the user
    device = FCMDevice.objects.filter(user=user).first()

    if device:
        result = device.send_message(
            Message(notification=Notification(title=title_msg, body=body_msg))
        )
        print(result)
    else:
        print(f"No device found for user {user.username}")
        

def send_bulk_notification(registrations, event):
    devices = FCMDevice.objects.filter(user__in=[reg.user for reg in registrations])
    for device in devices:
        body_msg = f"Event {event.name} details have been updated."
        device.send_message(Message(notification=Notification(title="主辦方更改了活動資訊", body=body_msg)))


