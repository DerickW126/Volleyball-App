# Create your models here.
# notifications/models.py
from django.db import models
from django.contrib.auth.models import User
from events.models import Event
from push_notifications.models import APNSDevice

class CustomAPNSDevice(APNSDevice):
    custom_user = models.OneToOneField('auth.User', on_delete=models.CASCADE)

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event_id = models.IntegerField(null=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.username} - {self.message}"
