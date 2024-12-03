from django.contrib import admin
from fcm_django.models import FCMDevice
from django.contrib import messages

def send_update_notification(modeladmin, request, queryset):
    title = "程式更新通知"
    message = "我們已推出新版本的「打排球吧」。請更新您的應用程式，以獲取最新功能與改進！"
    try:
        # Fetch all devices
        devices = FCMDevice.objects.all()
        
        # Send the notification
        result = devices.send_message(
            title=title,
            body=message, # Optional, enables notification sound
        )
        # Show a success message in the admin panel
        modeladmin.message_user(request, f"Notification sent successfully to {len(devices)} devices.", messages.SUCCESS)
    except Exception as e:
        # Show an error message in the admin panel
        modeladmin.message_user(request, f"Error sending notifications: {e}", messages.ERROR)

send_update_notification.short_description = "Send update notification to all users"

existing_admin = admin.site._registry[FCMDevice]
existing_admin.actions = list(existing_admin.actions or []) + [send_update_notification]