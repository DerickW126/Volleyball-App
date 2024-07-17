# users/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('profile/', views.profile, name='profile'),
    path('google-login/', views.GoogleLogin.as_view(), name='google_login'),
]

