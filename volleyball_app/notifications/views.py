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

class RegisterDeviceTokenView(generics.CreateAPIView):
    queryset = FCMDevice.objects.all()
    serializer_class = FCMDeviceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Set the user associated with this device
        serializer.save(user=request.user)
        
        return Response({"message": "Device registered successfully"}, status=status.HTTP_201_CREATED)

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
