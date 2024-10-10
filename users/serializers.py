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
    authorization_code = serializers.CharField()

    def validate(self, attrs):
        authorization_code = attrs.get('authorization_code')
        jwt_token = self._generate_apple_jwt()

        # Exchange the authorization code for tokens
        tokens = self._exchange_apple_code(authorization_code, jwt_token)

        # Extract the user's information (name, email) from the identity token
        id_token = tokens.get('id_token', None)
        user_data = self._get_user_data_from_apple(id_token)

        # Create or get the user in the system
        user = self._get_or_create_user(user_data)

        attrs['user'] = user
        return attrs

    def _generate_apple_jwt(self):
        private_key = settings.APPLE_PRIVATE_KEY  # Store your .p8 private key in your environment variables
        team_id = settings.APPLE_TEAM_ID
        client_id = settings.APPLE_CLIENT_ID  # This is your app's Bundle ID or Service ID
        key_id = settings.APPLE_KEY_ID  # Found in the Apple Developer portal

        headers = {
            'kid': key_id,  # Key ID from your private key
            'alg': 'ES256'  # Algorithm
        }

        payload = {
            'iss': team_id,  # Team ID
            'iat': int(time.time()),  # Issue time
            'exp': int(time.time()) + 15777000,  # Expiry time (6 months max)
            'aud': 'https://appleid.apple.com',  # Audience
            'sub': client_id  # The app's identifier
        }

        token = jwt.encode(payload, private_key, algorithm='ES256', headers=headers)
        return token

    def _exchange_apple_code(self, authorization_code, jwt_token):
        url = 'https://appleid.apple.com/auth/token'

        data = {
            'client_id': settings.APPLE_CLIENT_ID,
            'client_secret': jwt_token,  # The JWT token generated earlier
            'code': authorization_code,  # The authorization code from Apple
            'grant_type': 'authorization_code'
        }

        response = requests.post(url, data=data)
        if response.status_code == 200:
            return response.json()
        else:
            raise serializers.ValidationError("Unable to authenticate with Apple")

    def _get_user_data_from_apple(self, id_token):
        # Here, you will decode the id_token to extract user data (email, etc.)
        user_data = jwt.decode(id_token, options={"verify_signature": False})
        return user_data

    def _get_or_create_user(self, user_data):
        with transaction.atomic():
            try:
                user, created = CustomUser.objects.get_or_create(
                    username=user_data['email'],
                    defaults={'email': user_data['email'], 'first_name': user_data.get('name', {}).get('firstName', ''),
                              'last_name': user_data.get('name', {}).get('lastName', '')}
                )
                if created:
                    user.set_unusable_password()
                    user.save()

                social_account, social_created = SocialAccount.objects.get_or_create(
                    user=user, 
                    uid=user_data['sub'],  # 'sub' is the user's unique identifier from Apple
                    provider='apple'
                )

            except IntegrityError:
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