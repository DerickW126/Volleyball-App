# events/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),  # 根 URL 對應 index 視圖
    path('add/', views.add_event, name='add_event'),  # /add/ URL 對應 add_event 視圖
	path('register/<int:event_id>/', views.register_event, name='register_event'),
	path('unregister/<int:event_id>/', views.unregister_event, name='unregister_event'),
    path('api/events/', views.EventListAPIView.as_view(), name='api-events'),
    path('api/register/<int:event_id>/', views.RegisterEventAPIView.as_view(), name='api-register-event'),
    path('api/unregister/<int:event_id>/', views.UnregisterEventAPIView.as_view(), name='api-unregister-event'),
]

