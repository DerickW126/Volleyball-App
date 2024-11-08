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
import time
from django.contrib.auth import get_user_model
from .models import Report

CustomUser = get_user_model()
class AppleLoginSerializer(serializers.Serializer):
    authorization_code = serializers.CharField()
    useAppleUsername = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        authorization_code = attrs.get('authorization_code')
        use_apple_name = attrs.get('useAppleUsername', False)

        # Step 1: Generate JWT token to authenticate with Apple
        jwt_token = self._generate_apple_jwt()

        # Step 2: Exchange authorization code for identity token
        tokens = self._exchange_apple_code(authorization_code, jwt_token)

        # Step 3: Extract user data from the id_token
        id_token = tokens.get('id_token')
        if not id_token:
            raise serializers.ValidationError('Unable to retrieve id_token')

        user_data = self._get_user_data_from_apple(id_token)

        # Extract the first and last names if available
        decoded_token = jwt.decode(id_token, options={"verify_signature": False})
        first_name = decoded_token.get('given_name', '')
        last_name = decoded_token.get('family_name', '')

        # Step 4: Get or create the user in your system, passing the useAppleUsername flag and name
        user = self._get_or_create_user(user_data, first_name, last_name, use_apple_name)

        attrs['user'] = user
        return attrs

    def _generate_apple_jwt(self):
        """Generate the JWT token used to authenticate with Apple."""
        headers = {
            'kid': settings.APPLE_KEY_ID,
            'alg': 'ES256'
        }

        claims = {
            'iss': settings.APPLE_TEAM_ID,  # Your Apple Developer Team ID
            'iat': int(time.time()),        # Issue time
            'exp': int(time.time()) + 3600, # Expiry time
            'aud': 'https://appleid.apple.com',
            'sub': settings.APPLE_CLIENT_ID,  # Your app's client ID from Apple Developer
        }

        private_key = settings.APPLE_PRIVATE_KEY

        # Generate the client_secret JWT
        client_secret = jwt.encode(
            payload=claims,
            key=private_key,
            algorithm='ES256',
            headers=headers
        )

        return client_secret

    def _exchange_apple_code(self, authorization_code, jwt_token):
        """Exchange the authorization code for tokens from Apple."""
        data = {
            'client_id': settings.APPLE_CLIENT_ID,
            'client_secret': jwt_token,
            'code': authorization_code,
            'grant_type': 'authorization_code',
        }

        response = requests.post('https://appleid.apple.com/auth/token', data=data)
        response.raise_for_status()  # This will raise an error if the request fails
        return response.json()

    def _get_user_data_from_apple(self, id_token):
        """Decode the id_token from Apple to get user information."""
        decoded_token = jwt.decode(id_token, options={"verify_signature": False})
        email = decoded_token.get('email')
        apple_id = decoded_token.get('sub')

        # Check if email and apple_id are provided
        if not email:
            raise serializers.ValidationError("Apple did not provide an email. Please try logging in with Apple again.")
        if not apple_id:
            raise serializers.ValidationError("Apple ID is missing from the token.")

        return {
            'email': email,
            'apple_id': apple_id,
        }

    def _get_or_create_user(self, user_data, first_name='', last_name='', use_apple_name=False):
        """Get or create a user based on Apple user data."""
        email = user_data['email']
        apple_id = user_data['apple_id']

        # Validate that we have all the necessary information
        if not apple_id:
            raise serializers.ValidationError("Apple ID is missing")
        if not email:
            raise serializers.ValidationError("Email is missing")

        # Try to fetch the user based on the Apple ID or email
        user, created = CustomUser.objects.get_or_create(
            username=apple_id,
            defaults={'email': email}
        )

        # Set the nickname if the user is newly created and `useAppleUsername` is true
        if created:
            if use_apple_name and (first_name or last_name):
                user.nickname = f"{first_name} {last_name}".strip()
            user.save()

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

class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ['title', 'content', 'reported_user', 'reporter']
        read_only_fields = ['reporter', 'reported_user']
    
    def create(self, validated_data):
        return Report.objects.create(**validated_data)