from django.contrib import admin
from fcm_django.models import FCMDevice
from firebase_admin.messaging import Message, Notification
from django.contrib import messages
from .tasks import broadcast_update_notification

def send_update_notification(modeladmin, request, queryset):
    """
    An admin action that queues the broadcast task
    instead of sending directly in the HTTP request.
    """
    try:
        # If you want to ignore the selected queryset and send to ALL devices:
        broadcast_update_notification.delay()

        # Let the admin user know the task was queued successfully
        modeladmin.message_user(
            request, 
            "更新通知已加入佇列，稍後將寄送給所有 FCMDevice。",
            messages.SUCCESS
        )
    except Exception as e:
        modeladmin.message_user(
            request,
            f"Error queuing notifications: {e}",
            messages.ERROR
        )

send_update_notification.short_description = "Send update notification to all users"

existing_admin = admin.site._registry[FCMDevice]
existing_admin.actions = list(existing_admin.actions or []) + [send_update_notification]