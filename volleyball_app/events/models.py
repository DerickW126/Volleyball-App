# events/models.py
from django.db import models
from django.contrib.auth.models import User

class Event(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    cost = models.DecimalField(max_digits=6, decimal_places=2)
    additional_comments = models.TextField(blank=True, null=True)
    spots_left = models.IntegerField()
    created_by = models.ForeignKey(User, related_name='hosted_events', on_delete=models.CASCADE)
    attendees = models.ManyToManyField(User, through='Registration', related_name='registered_events', blank=True)

    def __str__(self):
        return self.name

class Registration(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    number_of_people = models.IntegerField(default=0)
    is_approved = models.BooleanField(default=False)

    class Meta:
        unique_together = ('event', 'user')

