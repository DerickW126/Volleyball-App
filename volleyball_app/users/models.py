from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
# Create your models here.
class CustomUser(AbstractUser):
    nickname = models.CharField(max_length=100, blank=True, null=True)

    groups = models.ManyToManyField(
        Group,
        related_name='customuser_set',  # Adjust the related name
        blank=True,
        help_text='The groups this user belongs to.',
        related_query_name='customuser'
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='customuser_set',  # Adjust the related name
        blank=True,
        help_text='Specific permissions for this user.',
        related_query_name='customuser'
    )
