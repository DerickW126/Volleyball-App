from django.shortcuts import render
# notifications/views.py
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Notification
from .serializers import NotificationSerializer
import requests
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework import status
from fcm_django.models import FCMDevice
from .serializers import FCMDeviceSerializer
from rest_framework.exceptions import ValidationError

class RegisterDeviceTokenView(generics.CreateAPIView):
    queryset = FCMDevice.objects.all()
    serializer_class = FCMDeviceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            registration_id = serializer.validated_data.get('registration_id')
            user = request.user

            # Check if the device already exists
            existing_device = FCMDevice.objects.filter(registration_id=registration_id).first()
            if existing_device:
                # Update the existing device's user
                existing_device.user = user
                existing_device.save()
                message = "Device already registered and updated successfully."
                status_code = status.HTTP_200_OK
            else:
                # Create a new device
                serializer.save(user=user)
                message = "Device registered successfully."
                status_code = status.HTTP_201_CREATED

        except ValidationError as e:
            # Handle validation errors
            return Response({"errors": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": message}, status=status_code)

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
