# users/views.py
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import GoogleLoginSerializer, UserSerializer, AppleLoginSerializer, ReportSerializer
from rest_framework import generics, permissions
from django.contrib.auth import logout, login
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from .models import Block
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
CustomUser = get_user_model()

class DeleteAccountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        user = request.user
        
        try:
            user.delete()
            return Response({"message": "Your account has been deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AppleLoginView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = AppleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        
        # Specify the backend explicitly (e.g., if you're using 'django.contrib.auth.backends.ModelBackend')
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        
        # Log the user in
        login(request, user)

        # Generate JWT refresh and access tokens
        refresh = RefreshToken.for_user(user)
        
        # Prepare response with tokens
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

class BlockUserView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        try:
            blocked_user = CustomUser.objects.get(id=user_id)
            if blocked_user == request.user:
                return Response({"error": "You cannot block yourself."}, status=status.HTTP_400_BAD_REQUEST)

            # Create a Block record if not already exists
            Block.objects.get_or_create(blocker=request.user, blocked=blocked_user)
            return Response({"message": "User blocked successfully."}, status=status.HTTP_201_CREATED)
        
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

class UnblockUserView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        try:
            blocked_user = CustomUser.objects.get(id=user_id)
            block = Block.objects.filter(blocker=request.user, blocked=blocked_user).first()
            if block:
                block.delete()
                return Response({"message": "User unblocked successfully."}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "User is not blocked."}, status=status.HTTP_400_BAD_REQUEST)
        
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [AllowAny]  # Allows read-only access without login

    def get_object(self):
        user_id = self.kwargs.get('user_id')
        try:
            user = CustomUser.objects.get(id=user_id)
            request_user = self.request.user

            # Check if the request user is authenticated and if the target user is blocked
            if request_user.is_authenticated:
                if Block.objects.filter(blocker=request_user, blocked=user).exists():
                    user.nickname = "用戶已被封鎖"
                    user.intro = "用戶已被封鎖"
                    return user

            return user
        except CustomUser.DoesNotExist:
            return None  # Handle non-existent users

    def retrieve(self, request, *args, **kwargs):
        user = self.get_object()

        if user is None:
            # User does not exist
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(user)
        return Response(serializer.data)
        
class BlockedUsersListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Get the list of users blocked by the requesting user
        blocked_user_ids = Block.objects.filter(blocker=self.request.user).values_list('blocked_id', flat=True)
        return CustomUser.objects.filter(id__in=blocked_user_ids)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class CreateReportView(generics.CreateAPIView):
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, user_id):
        reported_user = get_object_or_404(CustomUser, id=user_id)
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            # Set the reporter and reported_user fields
            serializer.save(reporter=request.user, reported_user=reported_user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)