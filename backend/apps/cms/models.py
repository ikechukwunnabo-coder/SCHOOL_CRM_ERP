from django.db import models
from django.utils import timezone

from apps.core.models import AuditableModel, InstitutionScopedModel


class CmsPage(InstitutionScopedModel, AuditableModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    slug = models.SlugField(max_length=120)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    is_public = models.BooleanField(default=True)

    class Meta:
        ordering = ["title"]
        constraints = [
            models.UniqueConstraint(fields=["institution", "slug"], name="uq_cms_page_slug")
        ]

    def __str__(self):
        return self.title


class CmsPost(InstitutionScopedModel, AuditableModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    class Kind(models.TextChoices):
        NEWS = "news", "News"
        EVENT = "event", "Event"
        NOTICE = "notice", "Notice"

    slug = models.SlugField(max_length=120)
    title = models.CharField(max_length=200)
    excerpt = models.TextField(blank=True)
    body = models.TextField(blank=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.NEWS)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    event_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["institution", "slug"], name="uq_cms_post_slug")
        ]


class CmsMenuItem(InstitutionScopedModel, AuditableModel):
    label = models.CharField(max_length=120)
    url = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    is_public = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "label"]


def publish_if_needed(obj):
    if obj.status == obj.Status.PUBLISHED and obj.published_at is None:
        obj.published_at = timezone.now()
