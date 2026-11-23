from django.contrib import admin

from .models import (
    AssessmentComponent,
    AssessmentScheme,
    GradingPolicy,
    GradingScale,
    ReportCard,
    ResultCorrection,
    ResultRecord,
    ResultWorkflowAction,
)

MODELS = (
    AssessmentScheme,
    AssessmentComponent,
    GradingScale,
    GradingPolicy,
    ResultRecord,
    ResultWorkflowAction,
    ResultCorrection,
    ReportCard,
)

for model in MODELS:
    admin.site.register(model)
