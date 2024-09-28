# users/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('api/profile/<int:user_id>/', views.UserProfileView.as_view(), name='user-profile'),
    path('google-login/', views.GoogleLogin.as_view(), name='google_login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('update-profile/', views.UpdateUserProfileView.as_view(), name='update-profile'),
    path('api/is-first-login/', views.IsFirstLoginAPIView.as_view(), name='is-first-login'),
]

