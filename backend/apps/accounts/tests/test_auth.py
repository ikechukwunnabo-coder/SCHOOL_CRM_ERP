import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.audit.models import AuditLog

User = get_user_model()


@pytest.mark.django_db
def test_csrf_endpoint_sets_cookie_and_returns_token():
    client = APIClient(enforce_csrf_checks=True)
    resp = client.get("/api/v1/auth/csrf/")
    assert resp.status_code == 200
    assert "csrfToken" in resp.data
    assert "csrftoken" in resp.cookies


@pytest.mark.django_db
def test_login_me_logout_flow_and_audit_logs():
    user = User.objects.create_user(
        email="user@example.com",
        password="StrongPass123!",
        is_active=True,
    )
    client = APIClient(enforce_csrf_checks=True)

    csrf = client.get("/api/v1/auth/csrf/").data["csrfToken"]
    login = client.post(
        "/api/v1/auth/login/",
        {"email": "user@example.com", "password": "StrongPass123!"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert login.status_code == 200
    assert login.data["user"]["email"] == "user@example.com"
    assert "sessionid" in login.cookies

    me = client.get("/api/v1/auth/me/")
    assert me.status_code == 200
    assert me.data["user"]["id"] == str(user.id)

    csrf2 = client.cookies.get("csrftoken").value
    logout = client.post(
        "/api/v1/auth/logout/",
        {},
        format="json",
        HTTP_X_CSRFTOKEN=csrf2,
    )
    assert logout.status_code == 204

    me_after = client.get("/api/v1/auth/me/")
    assert me_after.status_code in (401, 403)

    assert AuditLog.objects.filter(action="auth.login_succeeded", actor=user).exists()
    assert AuditLog.objects.filter(action="auth.logout", target_id=str(user.id)).exists()


@pytest.mark.django_db
def test_login_failure_returns_400_and_logs_attempt():
    client = APIClient(enforce_csrf_checks=True)
    csrf = client.get("/api/v1/auth/csrf/").data["csrfToken"]
    resp = client.post(
        "/api/v1/auth/login/",
        {"email": "missing@example.com", "password": "wrongpass"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert resp.status_code == 400
    assert "errors" in resp.data
    assert AuditLog.objects.filter(action="auth.login_failed").exists()
