from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.conf import settings

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
    skill_level = models.CharField(max_length=100, blank=True, null=True)

class Block(models.Model):
    blocker = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="blocked_users", on_delete=models.CASCADE)
    blocked = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="blocked_by_users", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked')
    

class Report(models.Model):
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="reports_made", on_delete=models.CASCADE)
    reported_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="reports_received", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report by {self.reporter} on {self.reported_user} - {self.title}"