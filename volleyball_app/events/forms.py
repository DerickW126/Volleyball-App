# events/forms.py
from django import forms
from .models import Event, Registration

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            'name', 'location', 'date', 'start_time', 'end_time', 
            'cost', 'additional_comments', 'spots_left'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }
class RegistrationForm(forms.ModelForm):
    class Meta:
        model = Registration
        fields = ['number_of_people']
