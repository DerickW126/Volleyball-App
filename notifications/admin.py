from django.contrib import admin
from fcm_django.models import FCMDevice
from firebase_admin.messaging import Message, Notification
from django.contrib import messages
from firebase_admin._messaging_utils import UnregisteredError


def send_update_notification(modeladmin, request, queryset):
    """
    Sends an update notification to each *selected* FCMDevice
    in the Django Admin.
    """
    title_msg = "程式更新通知"
    body_msg = "我們已推出新版本的「打排球吧」。請更新您的應用程式，以獲取最新功能與改進！"

    success_count = 0
    invalid_count = 0

    for device in queryset:
        try:
            # Send the notification to the specific device
            device.send_message(
                Message(notification=Notification(title=title_msg, body=body_msg))
            )
            success_count += 1
        except UnregisteredError:
            # This token is invalid/unregistered, so delete it
            device.delete()
            invalid_count += 1
        except Exception as e:
            # Other errors (network, etc.) won't remove the device
            print(f"Error sending to device {device.id}: {e}")

    # Provide feedback in the Admin UI
    modeladmin.message_user(
        request,
        f"通知已發送：{success_count} 個成功, {invalid_count} 個無效的token已被刪除。",
        level=messages.SUCCESS
    )

send_update_notification.short_description = "Send update notification to selected device(s)"
existing_admin = admin.site._registry[FCMDevice]
existing_admin.actions = list(existing_admin.actions or []) + [send_update_notification]