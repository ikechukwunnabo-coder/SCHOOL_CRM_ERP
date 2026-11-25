import pytest
from rest_framework import status

from apps.notifications.models import Notification, NotificationTemplate
from apps.permissions.models import Role, UserRole
from apps.permissions.roles import PARENT_GUARDIAN, REGISTRAR


@pytest.fixture
def base(db):
    from apps.institutions.models import Campus, Institution


    institution = Institution.objects.create(code="NOTIF", name="Notif Inst")
    campus = Campus.objects.create(
        institution=institution, code="MAIN", name="Main"
    )
    from django.contrib.auth import get_user_model

    User = get_user_model()
    registrar = User.objects.create_user(
        email="registrar@notif.test",
        password="pass12345",
        institution=institution,
        campus=campus,
    )
    parent = User.objects.create_user(
        email="parent@notif.test",
        password="pass12345",
        institution=institution,
        campus=campus,
    )
    Role.objects.get_or_create(name=REGISTRAR, defaults={"is_system": True})
    Role.objects.get_or_create(name=PARENT_GUARDIAN, defaults={"is_system": True})
    UserRole.objects.create(user=registrar, role=Role.objects.get(name=REGISTRAR))
    UserRole.objects.create(user=parent, role=Role.objects.get(name=PARENT_GUARDIAN))
    return institution, campus, registrar, parent


@pytest.mark.django_db
def test_notification_send_logs_status(base, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    institution, campus, registrar, _ = base
    n = Notification.objects.create(
        institution=institution,
        campus=campus,
        channel=NotificationTemplate.Channel.EMAIL,
        recipient_email="to@example.com",
        subject="Hello",
        body="Body",
        status=Notification.Status.PENDING,
    )
    from apps.notifications.services import send_notification

    sent = send_notification(actor=registrar, notification=n)
    assert sent.status == Notification.Status.SENT
    assert sent.sent_at is not None


@pytest.mark.django_db
def test_notification_dashboard_denies_parent(base):
    from rest_framework.test import APIClient

    institution, campus, _, parent = base
    Notification.objects.create(
        institution=institution,
        campus=campus,
        channel=NotificationTemplate.Channel.IN_APP,
        body="Body",
        status=Notification.Status.SENT,
    )
    client = APIClient()
    client.force_authenticate(user=parent)
    response = client.get("/api/v1/notifications/dashboard/")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_notification_dashboard_allows_registrar(base):
    from rest_framework.test import APIClient

    institution, campus, registrar, _ = base
    Notification.objects.create(
        institution=institution,
        campus=campus,
        channel=NotificationTemplate.Channel.IN_APP,
        body="Body",
        status=Notification.Status.SENT,
    )
    client = APIClient()
    client.force_authenticate(user=registrar)
    response = client.get("/api/v1/notifications/dashboard/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
