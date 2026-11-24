import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.institutions.models import Institution
from apps.notifications.models import Notification
from apps.permissions.models import Permission, Role, RolePermission, UserRole


def grant_role(user, *, institution, role_name):
    role, _ = Role.objects.get_or_create(
        name=role_name, defaults={"is_system": True, "institution": institution}
    )
    UserRole.objects.get_or_create(
        user=user,
        role=role,
        scope_type=UserRole.ScopeType.INSTITUTION,
        scope_ref_id=institution.id,
        defaults={"is_active": True},
    )
    for perm in Permission.objects.filter(module="notifications"):
        if role_name in (perm.allowed_role_names or []):
            RolePermission.objects.get_or_create(role=role, permission=perm)


@pytest.mark.django_db
def test_notification_send_logs_status(monkeypatch):
    inst = Institution.objects.create(name="Notif Inst", code="NOT")
    user = get_user_model().objects.create_user(
        email="notif@test.local", password="Passw0rd!123", institution=inst
    )
    grant_role(user, institution=inst, role_name="Registrar/Admissions")
    monkeypatch.setattr("apps.notifications.services.send_mail", lambda *args, **kwargs: 1)
    client = APIClient()
    client.force_authenticate(user=user)

    create = client.post(
        "/api/v1/notifications/templates/",
        {
            "institution": str(inst.id),
            "code": "FEE_DUE",
            "channel": "email",
            "subject": "Fee due",
            "body": "Please pay",
        },
        format="json",
    )
    assert create.status_code in {200, 201}

    n = Notification.objects.create(
        institution=inst,
        recipient_email="p@test.local",
        channel="email",
        subject="Hello",
        body="Body",
        status=Notification.Status.PENDING,
    )
    resp = client.post(f"/api/v1/notifications/logs/{n.id}/send/")
    assert resp.status_code == 200
    n.refresh_from_db()
    assert n.status == Notification.Status.SENT, n.error_message

