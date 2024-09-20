# users/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from allauth.socialaccount.models import SocialAccount
from django.db import transaction, IntegrityError
from events.serializers import EventSerializer
import requests
from django.conf import settings
from django.contrib.auth import get_user_model

CustomUser = get_user_model()

class GoogleLoginSerializer(serializers.Serializer):
    access_token = serializers.CharField()

    def validate(self, attrs):
        access_token = attrs.get('access_token')
        user_data = self._get_user_data_from_google(access_token)
        user = self._get_or_create_user(user_data)
        attrs['user'] = user
        return attrs

    def _get_user_data_from_google(self, access_token):
        response = requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            params={'access_token': access_token}
        )
        response.raise_for_status()
        return response.json()

    def _get_or_create_user(self, user_data):
        with transaction.atomic():
            try:
                user, created = CustomUser.objects.get_or_create(
                    username=user_data['email'],
                    defaults={'email': user_data['email'], 'first_name': user_data.get('given_name', ''), 'last_name': user_data.get('family_name', '')}
                )
                if created:
                    user.set_unusable_password()
                    user.save()

                social_account, social_created = SocialAccount.objects.get_or_create(
                    user=user, 
                    uid=user_data['id'], 
                    provider='google'
                )

            except IntegrityError:
                social_account = SocialAccount.objects.get(
                    uid=user_data['id'],
                    provider='google'
                )
                user = social_account.user

        return user

class UserSerializer(serializers.ModelSerializer):
    hosted_events = EventSerializer(many=True, read_only=True)
    registered_events = EventSerializer(many=True, read_only=True)
    
    class Meta:
        model = get_user_model()  # Use the custom user model
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'nickname', 'position', 'hosted_events', 'registered_events', 'intro']
    '''
    def update(self, instance, validated_data):
        # Update the fields you want to allow updating
        instance.nickname = validated_data.get('nickname', instance.nickname)
        instance.position = validated_data.get('position', instance.position)
        instance.intro = validated_data.get('intro', instance.intro)
        
        # You can add more fields here if you want to allow updating other attributes like first_name, etc.
        instance.save()
        return instance
    
    '''