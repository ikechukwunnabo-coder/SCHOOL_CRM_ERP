from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.permissions.permissions import (
    HasActiveInstitutionRole,
    HasInstitutionContext,
    HasModuleVerbPermission,
    IsAuthenticatedAndActive,
    IsCampusScoped,
    IsInstitutionScoped,
)

from .models import CmsMenuItem, CmsPage, CmsPost, publish_if_needed


def serializer_for(model_class, read_only=()):
    class Serializer(serializers.ModelSerializer):
        class Meta:
            model = model_class
            fields = "__all__"
            read_only_fields = [
                "id",
                "created_at",
                "updated_at",
                "created_by",
                "updated_by",
                *read_only,
            ]

    Serializer.__name__ = f"{model_class.__name__}Serializer"
    return Serializer


BASE = [
    IsAuthenticatedAndActive,
    HasInstitutionContext,
    HasActiveInstitutionRole,
    HasModuleVerbPermission,
    IsInstitutionScoped,
    IsCampusScoped,
]


class ScopedCmsViewSet(viewsets.ModelViewSet):
    permission_classes = BASE
    module = "cms"
    verb = "view"
    verb_map = {
        "create": "create",
        "update": "update",
        "partial_update": "update",
        "destroy": "delete_or_archive",
        "publish": "publish",
    }

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()
        user = self.request.user
        qs = self.queryset
        if user.is_superuser:
            return qs
        return qs.filter(institution_id=user.institution_id)

    def perform_create(self, serializer):
        user = self.request.user
        extra = {"created_by": user, "updated_by": user}
        if not user.is_superuser:
            extra["institution"] = user.institution
        obj = serializer.save(**extra)
        publish_if_needed(obj)
        if obj.published_at:
            obj.save(update_fields=["published_at"])

    def perform_update(self, serializer):
        user = self.request.user
        extra = {"updated_by": user}
        if not user.is_superuser:
            extra["institution"] = user.institution
        obj = serializer.save(**extra)
        publish_if_needed(obj)
        if obj.published_at:
            obj.save(update_fields=["published_at"])


class CmsPageViewSet(ScopedCmsViewSet):
    queryset = CmsPage.objects.select_related("institution")
    serializer_class = serializer_for(CmsPage, read_only=("published_at",))

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        obj = self.get_object()
        obj.status = CmsPage.Status.PUBLISHED
        publish_if_needed(obj)
        obj.updated_by = request.user
        obj.save(update_fields=["status", "published_at", "updated_by", "updated_at"])
        return Response(self.get_serializer(obj).data)


class CmsPostViewSet(ScopedCmsViewSet):
    queryset = CmsPost.objects.select_related("institution")
    serializer_class = serializer_for(CmsPost, read_only=("published_at",))

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        obj = self.get_object()
        obj.status = CmsPost.Status.PUBLISHED
        publish_if_needed(obj)
        obj.updated_by = request.user
        obj.save(update_fields=["status", "published_at", "updated_by", "updated_at"])
        return Response(self.get_serializer(obj).data)


class CmsMenuItemViewSet(ScopedCmsViewSet):
    queryset = CmsMenuItem.objects.select_related("institution")
    serializer_class = serializer_for(CmsMenuItem)


class PublicCmsViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    authentication_classes = []

    def _institution_id(self, request):
        return request.query_params.get("institution")

    @action(detail=False, methods=["get"], url_path="pages")
    def pages(self, request):
        qs = CmsPage.objects.filter(status=CmsPage.Status.PUBLISHED, is_public=True)
        inst = self._institution_id(request)
        if inst:
            qs = qs.filter(institution_id=inst)
        data = [
            {
                "slug": p.slug,
                "title": p.title,
                "body": p.body,
                "published_at": p.published_at,
            }
            for p in qs[:100]
        ]
        return Response(data)

    @action(detail=False, methods=["get"], url_path="posts")
    def posts(self, request):
        qs = CmsPost.objects.filter(status=CmsPost.Status.PUBLISHED)
        inst = self._institution_id(request)
        if inst:
            qs = qs.filter(institution_id=inst)
        kind = request.query_params.get("kind")
        if kind:
            qs = qs.filter(kind=kind)
        data = [
            {
                "slug": p.slug,
                "title": p.title,
                "excerpt": p.excerpt,
                "body": p.body,
                "kind": p.kind,
                "published_at": p.published_at,
                "event_date": p.event_date,
            }
            for p in qs[:100]
        ]
        return Response(data)

    @action(detail=False, methods=["get"], url_path="menu")
    def menu(self, request):
        qs = CmsMenuItem.objects.filter(is_public=True, is_active=True)
        inst = self._institution_id(request)
        if inst:
            qs = qs.filter(institution_id=inst)
        data = [{"label": m.label, "url": m.url, "order": m.order} for m in qs[:100]]
        return Response(data)
