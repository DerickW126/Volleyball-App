# notifications/urls.py
from django.urls import path
from .views import NotificationListView, MarkNotificationAsReadAPIView, RegisterDeviceTokenView

urlpatterns = [
    path('notifications/', NotificationListView.as_view(), name='notifications'),
    path('notifications/mark_as_read/<int:pk>/', MarkNotificationAsReadAPIView.as_view(), name='mark-notification-as-read'),
    path('register_device_token/', RegisterDeviceTokenView.as_view(), name='register_device_token'),
    #path('send_notification/', SendNotificationView.as_view(), name='send_notification'),
]
