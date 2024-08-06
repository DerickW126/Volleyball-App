# events/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),  # 根 URL 對應 index 視圖
    path('add/', views.add_event, name='add_event'),  # /add/ URL 對應 add_event 視圖
	path('register/<int:event_id>/', views.register_event, name='register_event'),
	path('unregister/<int:event_id>/', views.unregister_event, name='unregister_event'),
    
    path('api/events/', views.EventListAPIView.as_view(), name='api-events'), #All events
    path('api/event_detail/<int:pk>/', views.EventDetailAPIView.as_view(), name='event-detail'), #Event detail, shows all registrations
    path('api/events/add/', views.AddEventAPIView.as_view(), name='add-event'), #Add event
    path('api/register/<int:event_id>/', views.RegisterEventAPIView.as_view(), name='api-register-event'),
    path('api/unregister/<int:event_id>/', views.UnregisterEventAPIView.as_view(), name='api-unregister-event'),
    path('api/edit_registration/<int:pk>/', views.EditRegistrationAPIView.as_view(), name='edit-registration'),  
    path('api/check_registration/<int:event_id>', views.CheckRegistrationAPIView.as_view(), name='check_registration'),
    path('api/pending/', views.PendingRegistrationsAPIView.as_view(), name='pending-registrations'),
    path('api/approve/<int:registration_id>/', views.ApproveRegistrationAPIView.as_view(), name='approve-registration'),
    path('api/registrations/', views.UserRegistrationsAPIView.as_view(), name='user-registrations'),  
    path('verify_registration/<int:registration_id>/', views.VerifyUserRegistrationAPIView.as_view(), name='verify-registration'),  #Check if user is owner of registration
]

