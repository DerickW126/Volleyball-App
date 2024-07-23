# events/serializers.py
from rest_framework import serializers
from rest_framework import generics
from .models import Event, Registration

class RegistrationSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)  # 显示用户名而不是ID

    class Meta:
        model = Registration
        fields = ['id', 'user', 'number_of_people', 'is_approved']
        read_only_fields = ['is_approved']

class EventSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField(read_only=True)
    pending_registrations = serializers.SerializerMethodField()
    approved_registrations = serializers.SerializerMethodField()
    is_creator = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ['id', 'additional_comments','name', 'cost', 'location', 'date', 'start_time', 'end_time', 'spots_left', 'created_by', 'pending_registrations', 'approved_registrations', 'is_creator']

    def get_pending_registrations(self, obj):
        pending_registrations = Registration.objects.filter(event=obj, is_approved=False)
        return RegistrationSerializer(pending_registrations, many=True).data

    def get_approved_registrations(self, obj):
        approved_registrations = Registration.objects.filter(event=obj, is_approved=True)
        return RegistrationSerializer(approved_registrations, many=True).data
    
    def get_is_creator(self, obj):
        request = self.context.get('request', None)
        if request is None:
            return False
        return obj.created_by == request.user
