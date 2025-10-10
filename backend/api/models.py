from django.db import models

# Create your models here.

class VideoJob(models.Model):
    STATUS = [
        ("pending", "pending"),
        ("processing", "processing"),
        ("done", "done"),
        ("failed", "failed"),
    ]

    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=16, choices=STATUS, default="pending")
    original = models.FileField(upload_to="uploads/")
    outputs = models.JSONField(default=list, blank=True)  # ["outputs/<job>/<file>.avi", ...]
    error = models.TextField(blank=True, default="")

    def __str__(self):
        return f"VideoJob #{self.id} ({self.status})"