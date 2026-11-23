from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import api

app_name = "examinations"

router = DefaultRouter()
router.register("assessment-schemes", api.AssessmentSchemeViewSet, basename="assessment-scheme")
router.register(
    "assessment-components", api.AssessmentComponentViewSet, basename="assessment-component"
)
router.register("grading-scales", api.GradingScaleViewSet, basename="grading-scale")
router.register("results", api.ResultViewSet, basename="result")
router.register("report-cards", api.ReportCardViewSet, basename="report-card")

urlpatterns = [path("", include(router.urls))]
