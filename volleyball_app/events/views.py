# events/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .models import Event, Registration
from .forms import EventForm, RegistrationForm
from .serializers import EventSerializer, RegistrationSerializer
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from notifications.models import Notification

class EventListAPIView(generics.ListAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer

class RegisterEventAPIView(APIView):
    permission_classes = [IsAuthenticated]  # 确保用户登录

    def post(self, request, event_id):
        if not request.user.is_authenticated:
            return Response({"error": "User must be logged in to register for an event."}, status=status.HTTP_401_UNAUTHORIZED)

        event = get_object_or_404(Event, id=event_id)
        user = request.user
        
        registration, created = Registration.objects.get_or_create(event=event, user=user)
        
        previous_number = registration.number_of_people if not created else 0

        serializer = RegistrationSerializer(data=request.data, instance=registration)
        if serializer.is_valid():
            registration = serializer.save()  # 保存注册对象
            total_people = registration.number_of_people - previous_number

            if event.spots_left - total_people < 0:
                return Response({"error": "Not enough spots left for this number of people."}, status=status.HTTP_400_BAD_REQUEST)

            event.spots_left += previous_number  # 释放之前的注册名额
            event.spots_left -= registration.number_of_people  # 减少新的注册名额
            registration.save()
            event.save()

            # 创建新的通知
            if created:
                message = f"New registration: {user.username} has registered for your event {event.name}."
            else:
                message = f"Updated registration: {user.username} has updated their registration for your event {event.name}."

            Notification.objects.create(user=event.created_by, message=message)

            user_message = f"You have successfully registered for the event {event.name}."
            Notification.objects.create(user=user, message=user_message)

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
        
        event.spots_left += registration.number_of_people
        registration.delete()
        event.save()

        # 为取消注册的用户创建通知
        user_message = f"You have successfully unregistered from the event {event.name}."
        Notification.objects.create(user=user, message=user_message)

        # 为活动主办方创建通知
        host_message = f"{user.username} has unregistered from your event {event.name}."
        Notification.objects.create(user=event.created_by, message=host_message)

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

@login_required
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