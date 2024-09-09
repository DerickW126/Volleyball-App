# events/serializers.py
from rest_framework import serializers
from rest_framework import generics
from .models import Event, Registration, ChatMessage

class RegistrationSerializer(serializers.ModelSerializer):
    user_id = serializers.SerializerMethodField()  # Add this field
    user = serializers.StringRelatedField(read_only=True)  # Shows username instead of ID

    class Meta:
        model = Registration
        fields = ['id', 'user', 'user_id', 'number_of_people', 'is_approved', 'previously_approved']

    def get_user_id(self, obj):
        return obj.user.id

class EventSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField(read_only=True)
    created_by_id = serializers.IntegerField(source='created_by.id', read_only=True)
    pending_registrations = serializers.SerializerMethodField()
    approved_registrations = serializers.SerializerMethodField()
    is_creator = serializers.SerializerMethodField()
    pending_registration_count = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ['id', 'additional_comments','name', 'cost', 'location', 'date', 'start_time', 'end_time', 'spots_left', 'created_by', 'created_by_id', 'pending_registrations', 'approved_registrations', 'is_creator', 'pending_registration_count', 'net_type', 'status', 'cancellation_message']

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
    
    def get_pending_registration_count(self, obj):
        return obj.get_pending_registration_count()

class ChatMessageSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    user_first_name = serializers.SerializerMethodField()
    user_last_name = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = ['id', 'user_first_name', 'user_last_name', 'user', 'user_id', 'message', 'timestamp']

    def get_user_first_name(self, obj):
        return obj.user.first_name

    def get_user_last_name(self, obj):
        return obj.user.last_name