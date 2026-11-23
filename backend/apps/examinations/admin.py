from django.contrib import admin

from .models import (
    AssessmentComponent,
    AssessmentScheme,
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
    ResultRecord,
    ResultWorkflowAction,
    ResultCorrection,
    ReportCard,
)

for model in MODELS:
    admin.site.register(model)
