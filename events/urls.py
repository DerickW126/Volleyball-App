# events/urls.py
from django.urls import path
from .views import EventListAPIView, EventDetailAPIView, AddEventAPIView, RegisterEventAPIView, UnregisterEventAPIView, EditRegistrationAPIView, CheckRegistrationAPIView, PendingRegistrationsAPIView, ApproveRegistrationAPIView, UserRegistrationsAPIView, VerifyUserRegistrationAPIView, UpdateEventView, CancelEventView, RemoveUserFromApprovedListView, ChatMessageListView, SendMessageView, ActiveEventsListAPIView, InactiveEventsListAPIView

urlpatterns = [
    #path('', views.index, name='index'),  # 根 URL 對應 index 視圖
    #path('add/', views.add_event, name='add_event'),  # /add/ URL 對應 add_event 視圖
	#path('register/<int:event_id>/', views.register_event, name='register_event'),
	#path('unregister/<int:event_id>/', views.unregister_event, name='unregister_event'),
    
    path('api/events/', EventListAPIView.as_view(), name='api-events'), #All events
    path('api/event_detail/<int:pk>/', EventDetailAPIView.as_view(), name='event-detail'), #Event detail, shows all registrations
    path('api/events/add/', AddEventAPIView.as_view(), name='add-event'), #Add event
    path('api/register/<int:event_id>/', RegisterEventAPIView.as_view(), name='api-register-event'),
    path('api/unregister/<int:event_id>/', UnregisterEventAPIView.as_view(), name='api-unregister-event'),
    path('api/edit_registration/<int:pk>/', EditRegistrationAPIView.as_view(), name='edit-registration'),  
    path('api/check_registration/<int:event_id>', CheckRegistrationAPIView.as_view(), name='check_registration'),
    path('api/pending/', PendingRegistrationsAPIView.as_view(), name='pending-registrations'),
    path('api/approve/<int:registration_id>/', ApproveRegistrationAPIView.as_view(), name='approve-registration'),
    path('api/registrations/', UserRegistrationsAPIView.as_view(), name='user-registrations'),  
    path('verify_registration/<int:registration_id>/', VerifyUserRegistrationAPIView.as_view(), name='verify-registration'),  #Check if user is owner of registration
    path('events/update/<int:pk>/', UpdateEventView.as_view(), name='update-event'),
    path('events/cancel/<int:event_id>/', CancelEventView.as_view(), name='cancel-event'),
    path('events/<int:event_id>/remove_user/<int:user_id>/', RemoveUserFromApprovedListView.as_view(), name='remove_user_from_approved_list'),
    path('events/<int:event_id>/messages/', ChatMessageListView.as_view(), name='chat-message-list'),
    path('events/<int:event_id>/messages/send/', SendMessageView.as_view(), name='send-message'),
    path('events/active/', ActiveEventsListAPIView.as_view(), name='active-events'),
    path('events/inactive/', InactiveEventsListAPIView.as_view(), name='inactive-events'),
]


