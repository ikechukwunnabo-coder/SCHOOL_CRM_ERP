from rest_framework.routers import DefaultRouter

from .api import GuardianViewSet, StudentViewSet

router = DefaultRouter()
router.register("students", StudentViewSet, basename="student")
router.register("guardians", GuardianViewSet, basename="guardian")

urlpatterns = router.urls
