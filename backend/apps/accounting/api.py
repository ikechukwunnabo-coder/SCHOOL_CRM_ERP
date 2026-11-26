import csv

from django.db.models import Count, Sum
from django.http import HttpResponse
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
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

from .models import JournalEntry, JournalLine, LedgerAccount
from .services import AccountingError, approve_journal_entry, create_journal_entry

BASE = [
    IsAuthenticatedAndActive,
    HasInstitutionContext,
    HasActiveInstitutionRole,
    HasModuleVerbPermission,
    IsInstitutionScoped,
    IsCampusScoped,
]


class LedgerAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerAccount
        fields = [
            "id",
            "institution",
            "code",
            "name",
            "account_type",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "institution", "created_at", "updated_at"]


class JournalLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalLine
        fields = ["id", "entry", "account", "debit", "credit", "memo", "created_at", "updated_at"]
        read_only_fields = ["id", "entry", "created_at", "updated_at"]


class JournalEntrySerializer(serializers.ModelSerializer):
    lines = JournalLineSerializer(many=True, read_only=True)

    class Meta:
        model = JournalEntry
        fields = [
            "id",
            "institution",
            "campus",
            "reference",
            "description",
            "entry_date",
            "posted_by",
            "source_type",
            "source_id",
            "idempotency_key",
            "status",
            "posted_at",
            "lines",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "institution",
            "campus",
            "posted_by",
            "status",
            "posted_at",
            "lines",
            "created_at",
            "updated_at",
        ]


class JournalLineInputSerializer(serializers.Serializer):
    account = serializers.PrimaryKeyRelatedField(queryset=LedgerAccount.objects.all())
    debit = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, default="0.00"
    )
    credit = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, default="0.00"
    )
    memo = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class JournalEntryCreateSerializer(serializers.Serializer):
    institution = serializers.PrimaryKeyRelatedField(
        queryset=LedgerAccount.objects.none(), required=False
    )
    campus = serializers.PrimaryKeyRelatedField(
        queryset=LedgerAccount.objects.none(), required=False
    )
    reference = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    description = serializers.CharField(required=False, allow_blank=True, default="")
    entry_date = serializers.DateField()
    source_type = serializers.CharField(max_length=60, required=False, allow_blank=True, default="")
    source_id = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    idempotency_key = serializers.CharField(
        max_length=120, required=False, allow_blank=True, default=""
    )
    lines = JournalLineInputSerializer(many=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.institutions.models import Campus, Institution

        self.fields["institution"].queryset = Institution.objects.all()
        self.fields["campus"].queryset = Campus.objects.all()


class ScopedAccountingViewSet(viewsets.ModelViewSet):
    permission_classes = BASE
    module = "accounting"
    verb = "view"
    resource = "*"
    verb_map = {
        "create": "create",
        "update": "update",
        "partial_update": "update",
        "destroy": "delete_or_archive",
        "post": "approve",
        "approve": "approve",
    }

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
        if isinstance(exc, AccountingError):
            return super().handle_exception(ConflictError(detail=str(exc)))
        return super().handle_exception(exc)

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_superuser:
            serializer.save(institution=user.institution, posted_by=user)
        else:
            serializer.save(posted_by=user)

    def perform_update(self, serializer):
        user = self.request.user
        if not user.is_superuser:
            serializer.save(institution=user.institution)
        else:
            serializer.save()


class LedgerAccountViewSet(ScopedAccountingViewSet):
    queryset = LedgerAccount.objects.select_related("institution")
    serializer_class = LedgerAccountSerializer


class JournalEntryViewSet(ScopedAccountingViewSet):
    queryset = JournalEntry.objects.select_related(
        "institution", "campus", "posted_by"
    ).prefetch_related("lines")
    verb_map = {
        **ScopedAccountingViewSet.verb_map,
        "post": "update",
        "approve": "approve",
    }

    def get_serializer_class(self):
        if self.action == "create":
            return JournalEntryCreateSerializer
        return JournalEntrySerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request.user
        institution = data.pop("institution", None) or getattr(user, "institution", None)
        campus = data.pop("campus", None)
        if not user.is_superuser:
            institution = user.institution
            campus = user.campus
        if institution is None:
            raise ConflictError(detail="institution_required")
        try:
            entry, _ = create_journal_entry(
                actor=user, institution=institution, campus=campus, **data
            )
        except AccountingError as exc:
            raise ConflictError(detail=str(exc)) from exc
        return Response(
            JournalEntrySerializer(entry, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def post(self, request, *args, **kwargs):
        return self._approve(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def approve(self, request, *args, **kwargs):
        return self._approve(request, *args, **kwargs)

    def _approve(self, request, *args, **kwargs):
        entry = self.get_object()
        try:
            posted = approve_journal_entry(actor=request.user, entry=entry)
        except AccountingError as exc:
            raise ConflictError(detail=str(exc)) from exc
        return Response(JournalEntrySerializer(posted, context={"request": request}).data)


class AccountingDashboardViewSet(viewsets.ViewSet):
    permission_classes = BASE
    module = "accounting"
    verb = "view"
    verb_map = {"export_journal_entries": "export"}

    def _scoped_entries(self, request):
        user = request.user
        qs = JournalEntry.objects.all()
        if not user.is_superuser:
            qs = qs.filter(institution_id=user.institution_id)
            if user.campus_id:
                qs = qs.filter(campus_id=user.campus_id)
        return qs

    def list(self, request):
        user = request.user
        accounts = LedgerAccount.objects.all()
        entries = self._scoped_entries(request)
        if not user.is_superuser:
            accounts = accounts.filter(institution_id=user.institution_id)
        posted = entries.filter(status=JournalEntry.Status.POSTED)
        posted_lines = JournalLine.objects.filter(entry__in=posted)
        return Response(
            {
                "accounts": {
                    "count": accounts.count(),
                    "by_type": {
                        row["account_type"]: row["c"]
                        for row in accounts.values("account_type").annotate(c=Count("id"))
                    },
                },
                "journal_entries": {
                    "count": entries.count(),
                    "posted_count": posted.count(),
                    "draft_count": entries.filter(status=JournalEntry.Status.DRAFT).count(),
                    "by_status": {
                        row["status"]: row["c"]
                        for row in entries.values("status").annotate(c=Count("id"))
                    },
                    "posted_totals": {
                        "debit": str(posted_lines.aggregate(total=Sum("debit"))["total"] or 0),
                        "credit": str(posted_lines.aggregate(total=Sum("credit"))["total"] or 0),
                    },
                },
            }
        )

    @action(detail=False, methods=["get"], url_path="export-journal-entries")
    def export_journal_entries(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="journal-entries.csv"'
        writer = csv.writer(response)
        writer.writerow(
            ["id", "reference", "entry_date", "status", "description", "source_type", "source_id"]
        )
        for row in self._scoped_entries(request).order_by("-entry_date", "-created_at")[:5000]:
            writer.writerow(
                [
                    row.id,
                    row.reference,
                    row.entry_date.isoformat() if row.entry_date else "",
                    row.status,
                    row.description,
                    row.source_type,
                    row.source_id,
                ]
            )
        return response
