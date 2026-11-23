from rest_framework.routers import DefaultRouter

from .api import TranscriptRequestViewSet, TranscriptViewSet

router = DefaultRouter()
router.register("requests", TranscriptRequestViewSet, basename="transcript-request")
router.register("", TranscriptViewSet, basename="transcript")

urlpatterns = router.urls
