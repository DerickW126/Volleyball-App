from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
# Create your models here.

class CustomUser(AbstractUser):
    GENDER_CHOICES = [
        ('男', 'Male'),
        ('女', 'Female'),
    ]
    nickname = models.CharField(max_length=225, null=True, blank=True)
    position = models.CharField(max_length=225, null=True, blank=True)
    intro = models.TextField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
