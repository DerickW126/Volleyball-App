# users/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from allauth.socialaccount.models import SocialAccount
from django.db import transaction, IntegrityError   
from rest_framework.exceptions import ValidationError
from events.serializers import EventSerializer
import requests
import jwt
from django.conf import settings
from django.contrib.auth import get_user_model

CustomUser = get_user_model()
class AppleLoginSerializer(serializers.Serializer):
    identity_token = serializers.CharField()

    def validate(self, attrs):
        identity_token = attrs.get('identity_token')
        user_data = self._get_user_data_from_apple(identity_token)
        user = self._get_or_create_user(user_data)
        attrs['user'] = user
        return attrs

    def _get_user_data_from_apple(self, identity_token):
        try:
            # Decode the identity token from Apple
            decoded_token = jwt.decode(identity_token, options={"verify_signature": False})

            # Extract user info from the decoded token
            user_data = {
                'email': decoded_token.get('email'),
                'sub': decoded_token.get('sub'),  # Unique user identifier (Apple ID)
                'first_name': decoded_token.get('given_name', ''),
                'last_name': decoded_token.get('family_name', '')
            }

            # Ensure that email is provided. If email is hidden, Apple generates a private email.
            if not user_data.get('email'):
                raise ValidationError("Email not provided by Apple. Make sure 'email' is included in Apple's scope.")

            return user_data

        except jwt.ExpiredSignatureError:
            raise ValidationError("The identity token has expired.")
        except jwt.InvalidTokenError:
            raise ValidationError("Invalid identity token.")

    def _get_or_create_user(self, user_data):
        with transaction.atomic():
            try:
                # Get or create the user, using the email from Apple (could be the private relay email)
                user, created = CustomUser.objects.get_or_create(
                    username=user_data['email'],
                    defaults={
                        'email': user_data['email'],
                        'first_name': user_data.get('first_name', ''),
                        'last_name': user_data.get('last_name', '')
                    }
                )

                # If the user was newly created, set an unusable password
                if created:
                    user.set_unusable_password()
                    user.save()

                # Associate with a SocialAccount for Apple
                social_account, social_created = SocialAccount.objects.get_or_create(
                    user=user,
                    uid=user_data['sub'],  # This is the unique user identifier from Apple
                    provider='apple'
                )

            except IntegrityError:
                # Handle the case where the user already exists, linking to the social account
                social_account = SocialAccount.objects.get(
                    uid=user_data['sub'],
                    provider='apple'
                )
                user = social_account.user

        return user
        
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
        fields = ['id', 'username', 'gender', 'email', 'first_name', 'last_name', 'nickname', 'position', 'hosted_events', 'registered_events', 'intro']