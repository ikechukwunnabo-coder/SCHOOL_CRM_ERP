from rest_framework.routers import DefaultRouter

from .api import ApplicationDocumentViewSet, ApplicationViewSet, EnquiryViewSet

router = DefaultRouter()
router.register("enquiries", EnquiryViewSet, basename="enquiry")
router.register("applications", ApplicationViewSet, basename="application")
router.register(
    "application-documents",
    ApplicationDocumentViewSet,
    basename="application-document",
)

urlpatterns = router.urls
