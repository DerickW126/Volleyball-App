# events/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .models import Event, Registration
from .forms import EventForm, RegistrationForm
from .serializers import EventSerializer
from rest_framework import generics, status

class EventListAPIView(generics.ListAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer

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