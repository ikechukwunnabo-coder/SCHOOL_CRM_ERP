from rest_framework.routers import DefaultRouter

from .api import ImportJobViewSet

router = DefaultRouter()
router.register("imports", ImportJobViewSet, basename="import-job")

urlpatterns = router.urls
