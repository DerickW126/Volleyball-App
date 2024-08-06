# notifications/serializers.py
from rest_framework import serializers
from .models import Notification
from events.models import Event
from .models import CustomAPNSDevice
from push_notifications.models import APNSDevice

class APNSDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = APNSDevice
        fields = ('registration_id', 'user')
        extra_kwargs = {'user': {'read_only': True}}
class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['id', 'name', 'location', 'date', 'start_time', 'end_time']  # Include relevant fields

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'message', 'is_read', 'event_id']
        read_only_fields = ['id', 'message']

class CustomAPNSDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomAPNSDevice
        fields = ['registration_id', 'custom_user']
