"""
ASGI config for volleyball_app project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.layers import get_channel_layer
from django.urls import path
from notifications.consumers import NotificationConsumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'volleyball_app.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter([
            path('ws/notifications/<int:user_id>/', NotificationConsumer.as_asgi()),
        ])
    ),
})