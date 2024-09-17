# users/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('api/profile/<int:user_id>/', views.UserProfileView.as_view(), name='user-profile'),
    path('google-login/', views.GoogleLogin.as_view(), name='google_login'),
    path('facebook-login/', views.FacebookLogin.as_view(), name='facebook_login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
]

