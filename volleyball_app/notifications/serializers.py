# notifications/serializers.py
from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'message', 'is_read', 'timestamp']

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-timestamp')
