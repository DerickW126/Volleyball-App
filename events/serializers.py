# events/serializers.py
from rest_framework import serializers
from rest_framework import generics
from .models import Event, Registration, ChatMessage
from users.models import Block
from django.contrib.auth import get_user_model

CustomUser = get_user_model()

class RegistrationSerializer(serializers.ModelSerializer):
    user_id = serializers.SerializerMethodField()  # Add this field
    user = serializers.StringRelatedField(read_only=True)  # Shows username instead of ID
    user_nickname = serializers.SerializerMethodField()  # Add this line
    user_gender = serializers.SerializerMethodField() 
    class Meta:
        model = Registration
        fields = ['id', 'user', 'notes', 'user_id', 'user_nickname', 'user_gender', 'number_of_people', 'is_approved', 'previously_approved']

    def get_user_id(self, obj):
        return obj.user.id

    def get_user_nickname(self, obj):  # Add this method
        return obj.user.nickname
    
    def get_user_gender(self, obj):
        return obj.user.gender

class EventSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField(read_only=True)
    created_by_id = serializers.IntegerField(source='created_by.id', read_only=True)
    created_by_nickname = serializers.SerializerMethodField()
    pending_registrations = serializers.SerializerMethodField()
    approved_registrations = serializers.SerializerMethodField()
    is_creator = serializers.SerializerMethodField()
    pending_registration_count = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            'id', 'additional_comments', 'name', 'cost', 'location', 'date', 'start_time',
            'end_time', 'is_overnight', 'spots_left', 'created_by', 'created_by_id',
            'created_by_nickname', 'pending_registrations', 'approved_registrations',
            'is_creator', 'pending_registration_count', 'net_type', 'status',
            'cancellation_message'
        ]

    def get_created_by_nickname(self, obj):
        return obj.created_by.nickname if hasattr(obj.created_by, 'nickname') else None

    def get_pending_registrations(self, obj):
        pending_registrations = Registration.objects.filter(event=obj, is_approved=False)
        user = self.context.get('request').user
        if not user.is_authenticated:
            return []  # Return empty if the user is not authenticated
        return self._serialize_registrations(pending_registrations, user)

    def get_approved_registrations(self, obj):
        approved_registrations = Registration.objects.filter(event=obj, is_approved=True)
        user = self.context.get('request').user
        if not user.is_authenticated:
            return []  # Return empty if the user is not authenticated
        return self._serialize_registrations(approved_registrations, user)

    def get_is_creator(self, obj):
        request = self.context.get('request', None)
        if request is None or not request.user.is_authenticated:
            return False
        return obj.created_by == request.user

    def _serialize_registrations(self, registrations, viewer):
        serialized_data = []
        for registration in registrations:
            # Check if the viewer has blocked the user
            if viewer.is_authenticated and Block.objects.filter(blocker=viewer, blocked=registration.user).exists():
                registration_data = {
                    'user_nickname': 'Blocked',
                    'additional_comments': 'Blocked'
                }
            else:
                registration_data = RegistrationSerializer(registration).data
            serialized_data.append(registration_data)
        return serialized_data

class ChatMessageSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    user_first_name = serializers.SerializerMethodField()
    user_last_name = serializers.SerializerMethodField()
    user_nickname = serializers.SerializerMethodField() 
    class Meta:
        model = ChatMessage
        fields = ['id', 'user_first_name', 'user_last_name', 'user_nickname', 'user', 'user_id', 'message', 'timestamp']

    def get_user_first_name(self, obj):
        return obj.user.first_name

    def get_user_last_name(self, obj):
        return obj.user.last_name

    def get_user_nickname(self, obj):  # Add this method
        return obj.user.nickname

