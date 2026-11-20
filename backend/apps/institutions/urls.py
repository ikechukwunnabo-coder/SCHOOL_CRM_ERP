from rest_framework.routers import DefaultRouter

from .api import CampusViewSet, InstitutionViewSet

router = DefaultRouter()
router.register("institutions", InstitutionViewSet, basename="institution")
router.register("campuses", CampusViewSet, basename="campus")

urlpatterns = router.urls
