from rest_framework.routers import DefaultRouter

from .api import AlumniRecordViewSet

router = DefaultRouter()
router.register("records", AlumniRecordViewSet, basename="alumni-record")

urlpatterns = router.urls
