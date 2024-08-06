from django.shortcuts import render
# notifications/views.py
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status, permissions
from .models import Notification
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import NotificationSerializer
from .models import CustomAPNSDevice
from push_notifications.models import APNSDevice
from .serializers import CustomAPNSDeviceSerializer
import requests
from .serializers import APNSDeviceSerializer

def send_notification_direct(user, message):
    try:
        device = APNSDevice.objects.get(user=user)
        device.send_message(message)
        print(f"Notification sent to user {user_id}")
    except CustomAPNSDevice.DoesNotExist:
        print(f"Device for user {user_id} not found")

def trigger_notification(user, message):
    # Get the user's access token (this will depend on your auth setup)
    #access_token = user.get_access_token()  # Replace with your method of retrieving the token
    #jwt = user.get_jwt()
    headers = {
        #'Authorization': f'Bearer {jwt}',
        'Content-Type': 'application/json',
    }
    data = {
        'message': message,
    }
    try:
        response = requests.post('http://ec2-18-181-213-105.ap-northeast-1.compute.amazonaws.com:8000/api/send_notification/', headers=headers, json=data)
        response.raise_for_status()  # This will raise an HTTPError if the HTTP request returned an unsuccessful status code
        print("Notification sent successfully")
    except requests.exceptions.HTTPError as http_err:
        error_message = "An error occurred"
        try:
            # Try to parse JSON response to get the error message
            error_data = response.json()
            error_message = error_data.get('error', str(http_err))
        except (ValueError, requests.exceptions.JSONDecodeError):
            # Fall back if the response is not JSON
            if response.text:
                error_message = response.text[:1000]  # Limit output to the first 200 characters
            else:
                error_message = str(http_err)
        print(f"Failed to send notification: {error_message}")
    except Exception as err:
        print(f"An unexpected error occurred: {err}")
'''
class RegisterDeviceTokenView(generics.CreateAPIView):
    queryset = CustomAPNSDevice.objects.all()
    serializer_class = CustomAPNSDeviceSerializer
    permission_classes = [permissions.IsAuthenticated]
'''
class APNSDeviceRegisterView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = APNSDeviceSerializer(data=request.data)
        if serializer.is_valid():
            device, created = APNSDevice.objects.update_or_create(
                user=request.user,
                defaults={
                    'registration_id': serializer.validated_data['registration_id'],
                    'active': True
                }
            )
            return Response({"message": "Device registered successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SendNotificationView(generics.GenericAPIView):
    #permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            device = CustomAPNSDevice.objects.get(user=request.user)
            message = request.data.get('message', 'Default message')
            device.send_message(message)
            return Response({"message": "Notification sent"}, status=status.HTTP_200_OK)
        except CustomAPNSDevice.DoesNotExist:
            return Response({"error": "Device not registered"}, status=status.HTTP_400_BAD_REQUEST)

class MarkNotificationAsReadAPIView(generics.UpdateAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user != request.user:
            return Response({'error': 'You do not have permission to mark this notification as read.'}, status=status.HTTP_403_FORBIDDEN)
        
        instance.is_read = True
        instance.save()

        return Response({'success': 'Notification marked as read.'}, status=status.HTTP_200_OK)


class NotificationListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-timestamp')
