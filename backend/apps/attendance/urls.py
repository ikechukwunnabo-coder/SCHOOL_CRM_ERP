from rest_framework.routers import DefaultRouter

from .api import AttendanceCorrectionViewSet, AttendanceRecordViewSet, AttendanceSessionViewSet

router = DefaultRouter()
router.register("attendance-sessions", AttendanceSessionViewSet, basename="attendance-session")
router.register("attendance-records", AttendanceRecordViewSet, basename="attendance-record")
router.register(
    "attendance-corrections", AttendanceCorrectionViewSet, basename="attendance-correction"
)

urlpatterns = router.urls
