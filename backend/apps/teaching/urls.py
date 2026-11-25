from rest_framework.routers import DefaultRouter

from .api import (
    AssignmentViewSet,
    TeacherPortalViewSet,
    TimetableSlotViewSet,
    TimetableViewSet,
    WorkloadPolicyViewSet,
)

router = DefaultRouter()
router.register("teacher-assignments", AssignmentViewSet, basename="teacher-assignment")
router.register("workload-policies", WorkloadPolicyViewSet, basename="workload-policy")
router.register("timetables", TimetableViewSet, basename="timetable")
router.register("timetable-slots", TimetableSlotViewSet, basename="timetable-slot")
router.register("portal", TeacherPortalViewSet, basename="teacher-portal")

urlpatterns = router.urls
