# users/views.py
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import GoogleLoginSerializer, UserSerializer, AppleLoginSerializer
from rest_framework import generics, permissions
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from rest_framework.permissions import AllowAny
CustomUser = get_user_model()

class AppleLoginView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = AppleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        
        data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

        return Response(data, status=status.HTTP_200_OK)
        
class IsFirstLoginAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Check if the user is logging in for the first time
        is_first_login = request.user.is_first_login
        return Response({"is_first_login": is_first_login})

class UpdateUserProfileView(generics.UpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]  # Ensure the user is authenticated

    def get_object(self):
        # The object we want to update is the currently logged-in user
        print(self.request.user)
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        print("update method called")  # Debug: Check if `update` is called

        # Get the user object
        user = self.get_object()

        # Instantiate the serializer with the current user and incoming data
        serializer = self.get_serializer(user, data=request.data, partial=True)

        # Validate the data
        if not serializer.is_valid():
            # Print validation errors to see what is going wrong
            print(f"Validation errors: {serializer.errors}")
            return Response({'detail': 'Invalid data', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        # If valid, call perform_update
        self.perform_update(serializer)

        return Response({'detail': 'Profile updated successfully'}, status=status.HTTP_200_OK)

    def perform_update(self, serializer):
        print('perform update called!!!!!!!!')
        # Check if the data is valid before saving
        if not serializer.is_valid():
            print(f"Validation failed: {serializer.errors}")  # Print any validation errors
            return Response({'detail': 'Invalid data', 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        # If valid, save and return success response
        try:
            instance = serializer.save()
            return Response({'detail': 'Profile updated successfully'}, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"Error occurred while saving: {e}")  # Catch and print any errors during saving
            return Response({'detail': 'An error occurred', 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
class GoogleLogin(SocialLoginView):
    serializer_class = GoogleLoginSerializer
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client
    callback_url = 'http://localhost:8000/accounts/google/login/callback/'

    def post(self, request, *args, **kwargs):
        self.serializer = self.get_serializer(data=request.data)
        self.serializer.is_valid(raise_exception=True)
        self.user = self.serializer.validated_data['user']
        self.login()
        token = self.get_token(self.user)
        data = {
            'refresh': str(token),
            'access': str(token.access_token),
        }
        return Response(data, status=status.HTTP_200_OK)

    def get_token(self, user):
        refresh = RefreshToken.for_user(user)
        return refresh

class LogoutView(APIView):
    def post(self, request, *args, **kwargs):
        # Invalidate JWT tokens
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()  # Assuming you have configured token blacklist
                # Optionally, you can log out the user from the session
                logout(request)
                return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
            else:
                return Response({"detail": "Refresh token is missing."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": f"Error logging out: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        user_id = self.kwargs.get('user_id')
        try:
            user = CustomUser.objects.get(id=user_id)
            return user
        except User.DoesNotExist:
            raise Http404

