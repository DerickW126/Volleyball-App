# users/views.py
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import GoogleLoginSerializer

# users/views.py
from rest_framework import status
from rest_framework.response import Response
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import GoogleLoginSerializer

class GoogleLogin(SocialLoginView):
    serializer_class = GoogleLoginSerializer
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client
    callback_url = 'http://localhost:8000/accounts/google/login/callback/'

    def post(self, request, *args, **kwargs):
        self.serializer = self.get_serializer(data=request.data)
        self.serializer.is_valid(raise_exception=True)
        self.user = self.serializer.validated_data['user']
        self.login()
        token = self.get_token(self.user)
        data = {
            'refresh': str(token),
            'access': str(token.access_token),
        }
        return Response(data, status=status.HTTP_200_OK)

    def get_token(self, user):
        refresh = RefreshToken.for_user(user)
        return refresh


from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def profile(request):
    user = request.user
    hosted_events = user.hosted_events.all()  # 获取用户主持的事件
    registered_events = user.registered_events.all()
    return render(request, 'users/profile.html', {
        'user': user,
        'hosted_events': hosted_events,
        'registered_events': registered_events
    })
