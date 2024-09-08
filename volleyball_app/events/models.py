# events/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import pytz
import datetime
from notifications.tasks import schedule_notifications

def convert_to_utc(local_time, local_tz):
    local_tz = pytz.timezone(local_tz)
    local_time = local_tz.localize(local_time, is_dst=None)
    return local_time.astimezone(pytz.utc)

class EventManager(models.Manager):
    def get(self, *args, **kwargs):
        event = super().get(*args, **kwargs)
        event.update_status()  
        return event

    def filter(self, *args, **kwargs):
        events = super().filter(*args, **kwargs)
        for event in events:
            event.update_status()
        return events

    def all(self):
        events = super().all()
        for event in events:
            event.update_status()
        return events

class Event(models.Model):
    NET_TYPE_CHOICES = [
        ('beach_volleyball', '沙灘排球'),
        ('women_net_mixed', '女網混排'),
        ('women_net_women', '女網女排'),
        ('men_net_men', '男網男排'),
        ('men_net_mixed', '男網混排'),
        ('mixed_net', '人妖網'),
    ]
    STATUS_CHOICES = [
        ('open', '開放報名'),
        ('waitlist', '開放候補'),
        ('playing', '進行中'),
        ('past', '已結束'),
        ('canceled', '取消')
    ]

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
    net_type = models.CharField(max_length=50, choices=NET_TYPE_CHOICES, default=NET_TYPE_CHOICES[0])
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default=STATUS_CHOICES[0])
    cancellation_message = models.TextField(blank=True, null=True)  # Add this field

    objects = EventManager()

    def __str__(self):
        return self.name

    def get_pending_registration_count(self):
        pending_registrations = self.registrations.filter(is_approved=False)
        return sum(registration.number_of_people for registration in pending_registrations)
    
    def update_status(self):
        now = timezone.now()  # Current datetime in UTC

        # Combine date and time fields into datetime objects
        event_start_datetime = timezone.make_aware(
            datetime.datetime.combine(self.date, self.start_time)
        )
        event_end_datetime = timezone.make_aware(
            datetime.datetime.combine(self.date, self.end_time)
        )
        print(self.status)
        if self.status == 'canceled':
            self.status = 'canceled'
        elif now > event_end_datetime:
            self.status = 'past'
        elif event_start_datetime <= now <= event_end_datetime:
            self.status = 'playing'
        elif self.spots_left == 0:
            self.status = 'waitlist'
        else:
            self.status = 'open'
        
        self.save()
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Schedule notifications after saving the event
        if self.pk:  # Check if the event already exists
            schedule_notifications.delay(self.id)   

class Registration(models.Model):
    event = models.ForeignKey(Event, related_name='registrations', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    number_of_people = models.IntegerField(default=0)
    is_approved = models.BooleanField(default=False)
    previously_approved = models.BooleanField(default=False)  # 新增字段

    def save(self, *args, **kwargs):
        if not self.previously_approved and self.is_approved:
            self.previously_approved = True
        super().save(*args, **kwargs)
        
    class Meta:
        unique_together = ('event', 'user')


class ChatMessage(models.Model):
    event = models.ForeignKey(Event, related_name='messages', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='chat_messages', on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']