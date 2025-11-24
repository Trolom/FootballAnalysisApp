from django.contrib import admin
from .models import VideoJob

@admin.register(VideoJob)
class VideoJobAdmin(admin.ModelAdmin):
    # Customize the list view to easily see the job status and output
    list_display = ('id', 'created_at', 'status', 'error', 'original_name')
    list_filter = ('status',)
    search_fields = ('id',)

    @admin.display(description="Original Filename")
    def original_name(self, obj):
        return obj.original.name.split('/')[-1] if obj.original else 'N/A'

# OR the simplest way:
# admin.site.register(VideoJob)