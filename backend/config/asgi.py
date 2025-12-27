"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import api.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = ProtocolTypeRouter({
    # Standard HTTP requests go here
    "http": get_asgi_application(),
    
    # WebSocket requests go here
    "websocket": AuthMiddlewareStack(
        URLRouter(
            api.routing.websocket_urlpatterns
        )
    ),
})