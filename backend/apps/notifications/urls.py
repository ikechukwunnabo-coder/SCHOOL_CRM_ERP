from rest_framework.routers import DefaultRouter

from .api import NotificationTemplateViewSet, NotificationViewSet

app_name = "notifications"

router = DefaultRouter()
router.register("templates", NotificationTemplateViewSet, basename="notification-template")
router.register("logs", NotificationViewSet, basename="notification")

urlpatterns = router.urls
