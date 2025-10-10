from rest_framework import serializers
from .models import VideoJob

class VideoJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoJob
        fields = ["id","status","original","outputs","error","created_at"]
        read_only_fields = ["status","outputs","error","created_at"]
