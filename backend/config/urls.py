from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from api.views import VideoJobViewSet

router = DefaultRouter()
router.register(r"jobs", VideoJobViewSet, basename="jobs")


urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/", include(router.urls)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
