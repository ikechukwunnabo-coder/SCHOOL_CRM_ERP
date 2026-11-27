from rest_framework.routers import DefaultRouter

from .api import CmsMenuItemViewSet, CmsPageViewSet, CmsPostViewSet, PublicCmsViewSet

router = DefaultRouter()
router.register(r"pages", CmsPageViewSet, basename="cms-page")
router.register(r"posts", CmsPostViewSet, basename="cms-post")
router.register(r"menu-items", CmsMenuItemViewSet, basename="cms-menu-item")
router.register(r"public", PublicCmsViewSet, basename="cms-public")

urlpatterns = router.urls
