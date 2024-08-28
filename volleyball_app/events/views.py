# events/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .models import Event, Registration
from .forms import EventForm, RegistrationForm
from .serializers import EventSerializer, RegistrationSerializer
from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from notifications.models import Notification
from .serializers import RegistrationSerializer
from notifications.utils import send_notification, send_bulk_notification

def notify_user_about_event(user, event_id, message):
    # Create the notification
    notification = Notification.objects.create(
        user=user,
        message=message,
        event_id=event_id
    )
    send_notification(user, "新的通知", message)

class CancelEventView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, event_id, *args, **kwargs):
        cancellation_message = request.data.get('cancellation_message')

        if not cancellation_message:
            return Response({"error": "Cancellation message is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            event = Event.objects.get(id=event_id)
            
            # Check if the user making the request is the creator of the event
            if event.created_by != request.user:
                return Response({"error": "You are not authorized to cancel this event"}, status=status.HTTP_403_FORBIDDEN)
            
            event.status = ('canceled', '取消')
            event.cancellation_message = cancellation_message
            event.save()

            # Notify all users associated with the event
            users = event.attendees.all()
            for user in users:
                notify_user_about_event(user, event_id, cancellation_message)

            return Response({"message": "Event canceled and notifications sent"}, status=status.HTTP_200_OK)

        except Event.DoesNotExist:
            return Response({"error": "Event not found"}, status=status.HTTP_404_NOT_FOUND)


class UpdateEventView(generics.UpdateAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        event = super().get_object()
        if event.created_by != self.request.user:
            raise permissions.PermissionDenied("You do not have permission to edit this event.")
        #send_notification(event)
        return event
    
    def perform_update(self, serializer):
        super().perform_update(serializer)
        event = self.get_object()
        self.notify_users(event)

    def notify_users(self, event):
        registrations = event.registrations.all()  # Fetch all registrations
        send_bulk_notification(registrations, event)

class VerifyUserRegistrationAPIView(APIView):
    permission_classes = [IsAuthenticated]  # Ensure the user is authenticated

    def get(self, request, registration_id):
        registration = get_object_or_404(Registration, id=registration_id)
        user = request.user

        # Check if the registration belongs to the current user
        is_user_registration = registration.user == user

        return Response({'is_user_registration': is_user_registration})

class UserRegistrationsAPIView(generics.ListAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Registration.objects.filter(user=user)

class PendingRegistrationsAPIView(generics.ListAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Registration.objects.filter(event__created_by=user, is_approved=False)

class ApproveRegistrationAPIView(APIView):
    permission_classes = [IsAuthenticated]  # 确保用户登录

    def post(self, request, registration_id):
        registration = get_object_or_404(Registration, id=registration_id)
        event = registration.event

        if event.created_by != request.user:
            return Response({"error": "You are not authorized to approve this registration."}, status=status.HTTP_403_FORBIDDEN)

        if event.spots_left < registration.number_of_people:
            return Response({"error": "Not enough spots left for this number of people."}, status=status.HTTP_400_BAD_REQUEST)

        registration.is_approved = True
        event.spots_left -= registration.number_of_people
        registration.save()
        event.save()

        # 创建通知
        message = f"Your registration for the event {event.name} has been approved."
        notify_user_about_event(event.created_by, event.id, message)

        return Response({"success": "Registration approved successfully."}, status=status.HTTP_200_OK)

class EventDetailAPIView(generics.RetrieveAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]  # 允许任何人查看，但只有认证用户才能进行其他操作

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context
        
class AddEventAPIView(APIView):
    permission_classes = [IsAuthenticated]  # 确保用户登录

    def post(self, request):
        serializer = EventSerializer(data=request.data)
        if serializer.is_valid():
            event = serializer.save(created_by=request.user)
            message = f"{request.user.username}, You have successfully created {event.name}."
            #Notification.objects.create(user=event.created_by, message=message, event_id=event.id)
            notify_user_about_event(event.created_by, event.id, message)
            #send_notification_to_user(notification.id)
            return Response(EventSerializer(event).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class EventListAPIView(generics.ListAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer

class EditRegistrationAPIView(generics.UpdateAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Registration.objects.filter(user=self.request.user)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        if instance.user != request.user:
            raise PermissionDenied("You do not have permission to edit this registration.")
        
        data = request.data.copy()
        
        # If the registration was approved and is now being set to unapproved,
        # update the event's spots_left
        if instance.is_approved:
            event = instance.event
            event.spots_left += instance.number_of_people
            event.save()
            data['previously_approved'] = True  # Mark as previously approved

        data['is_approved'] = False  # Set to unapproved

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)

class RegisterEventAPIView(APIView):
    permission_classes = [IsAuthenticated]  # 确保用户登录

    def post(self, request, event_id):
        if not request.user.is_authenticated:
            return Response({"error": "User must be logged in to register for an event."}, status=status.HTTP_401_UNAUTHORIZED)

        event = get_object_or_404(Event, id=event_id)
        user = request.user
        
        registration, created = Registration.objects.get_or_create(event=event, user=user)
        send_notification(user, "註冊成功！", f"您已經成功申請註冊 {event.name}")
        serializer = RegistrationSerializer(data=request.data, instance=registration)
        if serializer.is_valid():
            registration = serializer.save()  
            if event.spots_left - registration.number_of_people < 0:
                return Response({"error": "Not enough spots left for this number of people."}, status=status.HTTP_400_BAD_REQUEST)
            registration.save()
            event.save()

            # 创建新的通知
            message = ""
            if created:
                message = f"New registration: {user.username} has requested to register for your event {event.name}."
            else:
                message = f"Updated registration: {user.username} has updated their request for your event {event.name}."

            #notification = Notification.objects.create(user=event.created_by, message=message, event_id=event_id)
            #send_notification_to_user(notification.id)
            notify_user_about_event(event.created_by, event_id, message)

            user_message = f"You have requested to register for the event {event.name}."
            #user_notification = Notification.objects.create(user=user, message=user_message, event_id=event_id)
            #send_notification_to_user(user_notification.id)
            notify_user_about_event(user, event_id, user_message)

            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UnregisterEventAPIView(APIView):
    permission_classes = [IsAuthenticated]  # 确保用户登录

    def post(self, request, event_id):
        if not request.user.is_authenticated:
            return Response({"error": "User must be logged in to unregister from an event."}, status=status.HTTP_401_UNAUTHORIZED)

        event = get_object_or_404(Event, id=event_id)
        user = request.user
        registration = get_object_or_404(Registration, event=event, user=user)
        
        # 只有当注册是已批准状态时才增加空位数量
        if registration.is_approved:
            event.spots_left += registration.number_of_people
            event.save()

        registration.delete()

        # 为取消注册的用户创建通知
        #print(f'EVENT_ID: {event.id}')
        user_message = f"You have successfully unregistered from the event {event.name}."
        #user_notification = Notification.objects.create(user=user, message=user_message, event_id=event.id)
        #send_notification_to_user(user_notification.id)
        notify_user_about_event(user, event_id, user_message)

        # 为活动主办方创建通知
        host_message = f"{user.username} has unregistered from your event {event.name}."
       # host_notification = Notification.objects.create(user=event.created_by, message=host_message, event_id=event.id)
        #send_notification_to_user(host_notification.id)
        notify_user_about_event(event.created_by, event_id, host_message)
        return Response({"success": "Unregistered successfully."}, status=status.HTTP_200_OK)

class CheckRegistrationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, event_id):
        event = get_object_or_404(Event, id=event_id)
        user = request.user
        registration = Registration.objects.filter(event=event, user=user).first()

        if registration:
            data = {
                'registered': True,
                'number_of_people': registration.number_of_people
            }
        else:
            data = {'registered': False}
        return Response(data, status=status.HTTP_200_OK)

def index(request):
    events = Event.objects.all()
    return render(request, 'events/index.html', {'events': events})

@login_required
def add_event(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.created_by = request.user
            event.save()
            return redirect('index')
    else:
        form = EventForm()
    return render(request, 'events/add_event.html', {'form': form})

@login_required
def register_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    try:
        registration = Registration.objects.get(event=event, user=request.user)
        previous_number = registration.number_of_people
        created = False
    except Registration.DoesNotExist:
        registration = Registration(event=event, user=request.user)
        previous_number = 0
        created = True

    if request.method == 'POST':
        form = RegistrationForm(request.POST, instance=registration)
        if form.is_valid():
            registration = form.save(commit=False)
            total_people = registration.number_of_people - previous_number

            if event.spots_left - total_people < 0:
                return HttpResponse("Error: Not enough spots left for this number of people.", status=400)

            # 恢复之前注册的人数
            event.spots_left += previous_number
            # 减去新的注册人数
            event.spots_left -= registration.number_of_people
            registration.save()
            event.save()
            return redirect('index')
    else:
        form = RegistrationForm(instance=registration)
    
    return render(request, 'events/register_event.html', {'event': event, 'form': form})

@login_required
def unregister_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    try:
        registration = Registration.objects.get(event=event, user=request.user)
    except Registration.DoesNotExist:
        return HttpResponse("Error: Registration not found.", status=404)
    
    if request.method == 'POST':
        event.spots_left += registration.number_of_people
        registration.delete()
        event.save()
        return redirect('index')
    
    return render(request, 'events/unregister_event.html', {'event': event})