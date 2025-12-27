from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/jobs/(?P<job_id>\d+)/$', consumers.VideoJobConsumer.as_asgi()),
]