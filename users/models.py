from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

@receiver(user_logged_in)
def check_first_login(sender, user, request, **kwargs):
    if user.is_first_login:
        # If it's their first login, set is_first_login to False
        user.is_first_login = False
        user.save()
        
class CustomUser(AbstractUser):
    GENDER_CHOICES = [
        ('男', 'Male'),
        ('女', 'Female'),
        ('不透露', 'none'), 
    ]
    nickname = models.CharField(max_length=225, null=True, blank=True)
    position = models.CharField(max_length=225, null=True, blank=True)
    intro = models.TextField(null=True, blank=True)
    gender = models.CharField(max_length=3, choices=GENDER_CHOICES, null=True, blank=True)
    is_first_login = models.BooleanField(default=True)
