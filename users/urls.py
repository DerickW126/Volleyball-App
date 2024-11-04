# users/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('api/profile/<int:user_id>/', views.UserProfileView.as_view(), name='user-profile'),
    path('google-login/', views.GoogleLogin.as_view(), name='google_login'),
    path('apple-login/', views.AppleLoginView.as_view(), name='apple-login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('update-profile/', views.UpdateUserProfileView.as_view(), name='update-profile'),
    path('api/is-first-login/', views.IsFirstLoginAPIView.as_view(), name='is-first-login'),
    path('delete-account/', views.DeleteAccountAPIView.as_view(), name='delete-account'),
    path('block/<int:user_id>/', views.BlockUserView.as_view(), name='block-user'),
    path('unblock/<int:user_id>/', views.UnblockUserView.as_view(), name='unblock-user'),
    path('blocked-list/', views.BlockedUsersListView.as_view(), name='blocked-list'),
    path('report/<int:user_id>/', views.CreateReportView.as_view(), name='create-report'),
]

