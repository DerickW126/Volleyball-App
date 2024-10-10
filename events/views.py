# events/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .models import Event, Registration, ChatMessage
from .forms import EventForm, RegistrationForm
from .serializers import EventSerializer, RegistrationSerializer
from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from notifications.models import Notification
from .serializers import RegistrationSerializer, ChatMessageSerializer
from notifications.utils import send_notification, send_bulk_notification
from notifications.tasks import cancel_old_notifications, schedule_reminders, schedule_event_status_updates, set_event_status
from django.utils import timezone
import datetime
from datetime import timedelta

def notify_user_about_event(user, event_id, title, message):
    # Create the notification
    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        event_id=event_id
    )
    send_notification(user, title, message)

class ChatMessageListView(APIView):
    def get(self, request, event_id):
        try:
            event = Event.objects.get(id=event_id)
            messages = ChatMessage.objects.filter(event=event)
            serializer = ChatMessageSerializer(messages, many=True)
            return Response(serializer.data)
        except Event.DoesNotExist:
            return Response({"error": "Event not found"}, status=status.HTTP_404_NOT_FOUND)

class SendMessageView(APIView):
    def post(self, request, event_id):
        try:
            event = Event.objects.get(id=event_id)
            user = request.user
            message = request.data.get('message')
            
            if not message:
                return Response({"error": "Message cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)
            
            chat_message = ChatMessage.objects.create(event=event, user=user, message=message)
            serializer = ChatMessageSerializer(chat_message)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Event.DoesNotExist:
            return Response({"error": "Event not found"}, status=status.HTTP_404_NOT_FOUND)

class RemoveUserFromApprovedListView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, event_id, user_id, *args, **kwargs):
        cancellation_message = request.data.get('message')

        if not cancellation_message:
            return Response({"error": "Message is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Fetch the event
            event = Event.objects.get(id=event_id)
            
            # Check if the user making the request is the creator of the event
            if event.created_by != request.user:
                return Response({"error": "You are not authorized to remove users from this event"}, status=status.HTTP_403_FORBIDDEN)
            
            # Fetch the registration for the user
            registration = Registration.objects.get(event=event, user_id=user_id)
            
            # Check if the user is approved
            if registration.is_approved:
                # Remove user from the approved list by updating the registration status
                registration.is_approved = False
                event.spots_left += registration.number_of_people
                if event.status == 'waitlist' and event.spots_left > 0:
                    event.status = 'open'
                event.save()
                registration.save()
                
                # Notify the user about the change
                notify_user_about_event(registration.user, event_id, "報名更改通知", f"{event.name} 的活動發起人已將您移出參加名單。原因: {cancellation_message}")
                
                return Response({"message": "User removed from the approved list successfully"}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "User is not approved for this event"}, status=status.HTTP_400_BAD_REQUEST)
        
        except Event.DoesNotExist:
            return Response({"error": "Event not found"}, status=status.HTTP_404_NOT_FOUND)
        except Registration.DoesNotExist:
            return Response({"error": "Registration not found"}, status=status.HTTP_404_NOT_FOUND)

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
            
            event.status = 'canceled'
            event.cancellation_message = cancellation_message
            event.save()
            print(event.status)
            cancel_old_notifications(event)
            notify_user_about_event(request.user, event_id, "活動取消通知", f'您已成功取消這個活動 原因: {cancellation_message}')
            # Notify all users associated with the event
            users = event.attendees.all()
            for user in users:
                if user != request.user:
                    notify_user_about_event(user, event_id, "活動取消通知", f'您報名的活動 {event.name} 已被取消，原因: {cancellation_message}')

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
        return event
    
    def perform_update(self, serializer):
        event = self.get_object()

        old_event_start_datetime = timezone.make_aware(
            datetime.datetime.combine(event.date, event.start_time)
        )

        # Perform the actual update
        super().perform_update(serializer)

        # Fetch the updated event object
        updated_event = self.get_object()

        # Get the new event start time after the update
        new_event_start_datetime = timezone.make_aware(
            datetime.datetime.combine(updated_event.date, updated_event.start_time)
        )

        # Compare old and new event start times, and update reminders only if they differ
        if old_event_start_datetime != new_event_start_datetime:
            cancel_old_notifications(event)  # Cancel old reminders
            schedule_reminders(updated_event)  # Schedule new reminders

        self.notify_users(updated_event)

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
        if event.spots_left == 0:
            now = timezone.now()
            set_event_status.apply_async((event.id, 'waitlist'), eta=now + timedelta(seconds=5))
            
        registration.save()
        event.save()

        # 创建通知 
        message = f"你的在 {event.name} 已被審核通過，請準時抵達活動地點"
        notify_user_about_event(registration.user, event.id, '報名審核通過', message)

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
            schedule_event_status_updates(event)
            message = f"您已成功建立 {event.name}"
            notify_user_about_event(event.created_by, event.id, f'活動 {event.name} 創建成功', message)
            schedule_reminders(event)
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
        if instance.number_of_people > instance.event.spots_left:
            return Response({"error": "Not enough spots left for this number of people."}, status=status.HTTP_400_BAD_REQUEST)
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
        #send_notification(user, "註冊成功！", f"您已經成功申請註冊 {event.name}")
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
                message = f"新的報名： {user.username} 已申請報名您的活動 {event.name}，請儘速審核"
            else:
                message = f"更改的報名: {user.username} 已更改他在 {event.name} 的報名資訊，請儘速審核"

            #notification = Notification.objects.create(user=event.created_by, message=message, event_id=event_id)
            #send_notification_to_user(notification.id)
            notify_user_about_event(event.created_by, event_id, '報名通知', message)

            user_message = f"您已成功報名 {event.name}"
            #user_notification = Notification.objects.create(user=user, message=user_message, event_id=event_id)
            #send_notification_to_user(user_notification.id)
            notify_user_about_event(user, event_id, '報名通知', user_message)

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

        user_message = f"您已成功取消 {event.name} 的報名"
        notify_user_about_event(user, event_id,'報名通知', user_message)

        host_message = f"{user.username} 取消了他在 {event.name} 的報名"
        notify_user_about_event(event.created_by, event_id, '報名通知', host_message)
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