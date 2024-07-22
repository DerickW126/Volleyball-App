# users/urls.py
from django.urls import path
from . import views

urlpatterns = [
    #path('profile/', views.profile, name='profile'),
    path('api/profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('google-login/', views.GoogleLogin.as_view(), name='google_login'),
]

