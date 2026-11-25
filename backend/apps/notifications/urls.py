from rest_framework.routers import DefaultRouter

from .api import (
    NotificationDashboardViewSet,
    NotificationTemplateViewSet,
    NotificationViewSet,
)

app_name = "notifications"

router = DefaultRouter()
router.register("templates", NotificationTemplateViewSet, basename="notification-template")
router.register("logs", NotificationViewSet, basename="notification")
router.register("dashboard", NotificationDashboardViewSet, basename="notification-dashboard")

urlpatterns = router.urls
