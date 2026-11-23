from rest_framework.routers import DefaultRouter

from .api import AssignmentViewSet, TimetableSlotViewSet, TimetableViewSet

router = DefaultRouter()
router.register("teacher-assignments", AssignmentViewSet, basename="teacher-assignment")
router.register("timetables", TimetableViewSet, basename="timetable")
router.register("timetable-slots", TimetableSlotViewSet, basename="timetable-slot")

urlpatterns = router.urls
