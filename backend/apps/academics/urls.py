from rest_framework.routers import DefaultRouter

from .api import (
    ArmViewSet,
    ClassEnrolmentViewSet,
    ClassLevelViewSet,
    SessionViewSet,
    SubjectOfferingViewSet,
    SubjectViewSet,
    TermViewSet,
)

router = DefaultRouter()
router.register("academic-sessions", SessionViewSet, basename="academic-session")
router.register("terms", TermViewSet, basename="term")
router.register("class-levels", ClassLevelViewSet, basename="class-level")
router.register("arms", ArmViewSet, basename="arm")
router.register("subjects", SubjectViewSet, basename="subject")
router.register("subject-offerings", SubjectOfferingViewSet, basename="subject-offering")
router.register("class-enrolments", ClassEnrolmentViewSet, basename="class-enrolment")

urlpatterns = router.urls
