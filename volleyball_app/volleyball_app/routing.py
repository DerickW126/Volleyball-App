from django.urls import re_path
from volleyball_app.events import consumers

websocket_urlpatterns = [
    re_path(r'ws/events/(?P<event_id>\d+)/chat/$', consumers.ChatConsumer.as_asgi()),
]