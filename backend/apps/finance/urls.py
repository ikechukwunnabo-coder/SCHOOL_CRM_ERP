from rest_framework.routers import DefaultRouter

from .api import (
    FeeCategoryViewSet,
    FeeScheduleViewSet,
    FinancialAdjustmentViewSet,
    InvoiceViewSet,
    PaymentViewSet,
    PaymentWebhookViewSet,
    ReconciliationRecordViewSet,
)

app_name = "finance"

router = DefaultRouter()
router.register("fee-categories", FeeCategoryViewSet, basename="fee-category")
router.register("fee-schedules", FeeScheduleViewSet, basename="fee-schedule")
router.register("invoices", InvoiceViewSet, basename="invoice")
router.register("payments", PaymentViewSet, basename="payment")
router.register("adjustments", FinancialAdjustmentViewSet, basename="financial-adjustment")
router.register(
    "reconciliation-records", ReconciliationRecordViewSet, basename="reconciliation-record"
)
router.register("webhooks/payments", PaymentWebhookViewSet, basename="payment-webhook")

urlpatterns = router.urls
