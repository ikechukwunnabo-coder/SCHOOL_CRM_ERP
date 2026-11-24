from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.core.exceptions import ConflictError
from apps.permissions.permissions import (
    HasActiveInstitutionRole,
    HasInstitutionContext,
    HasModuleVerbPermission,
    IsAuthenticatedAndActive,
    IsCampusScoped,
    IsInstitutionScoped,
)

from . import services
from .models import (
    FeeCategory,
    FeeSchedule,
    FinancialAdjustment,
    Invoice,
    Payment,
    PaymentWebhookEvent,
)
from .services import FinanceError

BASE = [
    IsAuthenticatedAndActive,
    HasInstitutionContext,
    HasActiveInstitutionRole,
    HasModuleVerbPermission,
    IsInstitutionScoped,
    IsCampusScoped,
]


def serializer_for(model, *, read_only=(), extra_fields=None):
    extra_fields = extra_fields or {}

    class Serializer(serializers.ModelSerializer):
        class Meta:
            pass

    for name, field in extra_fields.items():
        Serializer._declared_fields[name] = field
    Serializer.Meta.model = model
    Serializer.Meta.fields = "__all__"
    Serializer.Meta.read_only_fields = [
        "id",
        "created_at",
        "updated_at",
        *read_only,
    ]
    return Serializer


class ScopedFinanceViewSet(viewsets.ModelViewSet):
    module = "finance"
    verb = "view"
    resource = "*"
    verb_map = {
        "create": "create",
        "update": "update",
        "partial_update": "update",
        "destroy": "delete_or_archive",
        "list": "view",
        "retrieve": "view",
    }
    permission_classes = BASE

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()
        user = self.request.user
        qs = self.queryset
        if user.is_superuser:
            return qs
        qs = qs.filter(institution_id=user.institution_id)
        if user.campus_id and hasattr(self.queryset.model, "campus_id"):
            qs = qs.filter(campus_id=user.campus_id)
        return qs

    def handle_exception(self, exc):
        if isinstance(exc, FinanceError):
            return super().handle_exception(ConflictError(detail=str(exc)))
        return super().handle_exception(exc)

    def perform_create(self, serializer):
        user = self.request.user
        save_kwargs = {}
        if hasattr(serializer.Meta.model, "institution_id") and not user.is_superuser:
            save_kwargs["institution"] = user.institution
        if hasattr(serializer.Meta.model, "campus_id") and not user.is_superuser:
            save_kwargs["campus"] = user.campus
        serializer.save(**save_kwargs)


class FeeCategoryViewSet(ScopedFinanceViewSet):
    queryset = FeeCategory.objects.select_related("institution", "campus")
    serializer_class = serializer_for(FeeCategory)


class FeeScheduleViewSet(ScopedFinanceViewSet):
    queryset = FeeSchedule.objects.select_related(
        "institution", "campus", "session", "term", "class_level", "category"
    )
    serializer_class = serializer_for(FeeSchedule)


class InvoiceLineInputSerializer(serializers.Serializer):
    description = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2, default="1.00")
    unit_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    category = serializers.UUIDField(required=False, allow_null=True)
    fee_schedule = serializers.UUIDField(required=False, allow_null=True)


class InvoiceCreateSerializer(serializers.ModelSerializer):
    lines = InvoiceLineInputSerializer(many=True, write_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "institution",
            "campus",
            "student",
            "session",
            "term",
            "due_date",
            "notes",
            "lines",
            "invoice_number",
            "currency",
            "total_amount",
            "balance_amount",
            "status",
            "issued_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "invoice_number",
            "currency",
            "total_amount",
            "balance_amount",
            "status",
            "issued_at",
            "created_at",
        ]


class InvoiceViewSet(ScopedFinanceViewSet):
    queryset = Invoice.objects.select_related("institution", "campus", "student", "session", "term")
    serializer_class = serializer_for(
        Invoice,
        read_only=[
            "invoice_number",
            "total_amount",
            "balance_amount",
            "status",
            "issued_at",
            "created_by",
        ],
    )
    verb_map = {
        **ScopedFinanceViewSet.verb_map,
        "issue": "update",
    }

    def get_serializer_class(self):
        if self.action == "create":
            return InvoiceCreateSerializer
        return super().get_serializer_class()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        actor = request.user
        institution = data.get("institution") or actor.institution
        if not actor.is_superuser and institution != actor.institution:
            raise PermissionDenied("cross_institution_access")
        invoice = services.create_invoice(
            actor=actor,
            institution=institution,
            student=data["student"],
            campus=data.get("campus"),
            session=data.get("session"),
            term=data.get("term"),
            due_date=data.get("due_date"),
            notes=data.get("notes", ""),
            lines=data.get("lines", []),
        )
        return Response(self.get_serializer(invoice).data, status=201)

    @action(detail=True, methods=["post"])
    def issue(self, request, pk=None):
        invoice = self.get_object()
        updated = services.issue_invoice(actor=request.user, invoice=invoice)
        return Response(self.get_serializer(updated).data)


class PaymentAllocationInputSerializer(serializers.Serializer):
    invoice = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)


class PaymentCreateSerializer(serializers.ModelSerializer):
    allocations = PaymentAllocationInputSerializer(many=True, required=False, write_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "institution",
            "campus",
            "student",
            "amount",
            "currency",
            "method",
            "provider",
            "provider_ref",
            "idempotency_key",
            "notes",
            "allocations",
            "receipt_number",
            "status",
            "received_at",
            "verified_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "receipt_number",
            "status",
            "received_at",
            "verified_at",
            "created_at",
        ]


class PaymentViewSet(ScopedFinanceViewSet):
    queryset = Payment.objects.select_related("institution", "campus", "student", "posted_by")
    serializer_class = serializer_for(
        Payment,
        read_only=["receipt_number", "status", "received_at", "verified_at", "posted_by"],
    )

    def get_serializer_class(self):
        if self.action == "create":
            return PaymentCreateSerializer
        return super().get_serializer_class()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        actor = request.user
        institution = data.get("institution") or actor.institution
        if not actor.is_superuser and institution != actor.institution:
            raise PermissionDenied("cross_institution_access")
        allocations = data.get("allocations", [])
        payment = services.record_payment(
            actor=actor,
            institution=institution,
            student=data.get("student"),
            campus=data.get("campus"),
            amount=data["amount"],
            currency=data.get("currency", "NGN"),
            method=data.get("method", "manual"),
            provider=data.get("provider", ""),
            provider_ref=data.get("provider_ref", ""),
            idempotency_key=data.get("idempotency_key", ""),
            notes=data.get("notes", ""),
            allocations=allocations,
        )
        return Response(self.get_serializer(payment).data, status=201)


class FinancialAdjustmentViewSet(ScopedFinanceViewSet):
    queryset = FinancialAdjustment.objects.select_related(
        "institution", "campus", "invoice", "payment", "requested_by", "approved_by", "applied_by"
    )
    serializer_class = serializer_for(
        FinancialAdjustment,
        read_only=["status", "approved_by", "applied_by", "applied_at"],
    )
    verb_map = {
        **ScopedFinanceViewSet.verb_map,
        "approve": "approve",
        "apply": "reverse_or_refund",
    }

    def perform_create(self, serializer):
        actor = self.request.user
        institution = serializer.validated_data.get("institution") or actor.institution
        if not actor.is_superuser and institution != actor.institution:
            raise PermissionDenied("cross_institution_access")
        adjustment = services.request_adjustment(
            actor=actor,
            institution=institution,
            adjustment_type=serializer.validated_data["adjustment_type"],
            amount=serializer.validated_data["amount"],
            reason=serializer.validated_data["reason"],
            currency=serializer.validated_data.get("currency", "NGN"),
            invoice=serializer.validated_data.get("invoice"),
            payment=serializer.validated_data.get("payment"),
            campus=serializer.validated_data.get("campus"),
        )
        serializer.instance = adjustment

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(self.get_serializer(serializer.instance).data, status=201)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        adjustment = self.get_object()
        updated = services.approve_adjustment(actor=request.user, adjustment=adjustment)
        return Response(self.get_serializer(updated).data)

    @action(detail=True, methods=["post"])
    def apply(self, request, pk=None):
        adjustment = self.get_object()
        updated = services.apply_adjustment(actor=request.user, adjustment=adjustment)
        return Response(self.get_serializer(updated).data)


class PaymentWebhookViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    authentication_classes = []

    @action(detail=False, methods=["post"], url_path=r"(?P<provider>[^/.]+)")
    def receive(self, request, provider=None):
        signature = request.headers.get("X-Webhook-Signature", "")
        raw_body = request.body or b""
        payload = request.data if isinstance(request.data, dict) else {}
        event = services.process_payment_webhook(
            provider=provider,
            raw_body=raw_body,
            signature=signature,
            payload=payload,
        )
        status_code = (
            status.HTTP_200_OK
            if event.status != PaymentWebhookEvent.Status.FAILED
            else status.HTTP_400_BAD_REQUEST
        )
        return Response(
            {
                "id": str(event.id),
                "provider": event.provider,
                "event_id": event.event_id,
                "status": event.status,
                "processing_detail": event.processing_detail,
                "payment_id": str(event.payment_id) if event.payment_id else None,
            },
            status=status_code,
        )
