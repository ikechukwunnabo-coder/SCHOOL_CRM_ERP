import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.institutions.models import Campus, Institution
from apps.permissions.models import Role, UserRole

User = get_user_model()


def create_institution(code):
    return Institution.objects.create(name=code.title(), code=code)


def grant_role(user, institution=None, name="Admin", is_active=True):
    role = Role.objects.create(name=name, institution=institution)
    UserRole.objects.create(user=user, role=role, is_active=is_active)


@pytest.mark.django_db
def test_unauthenticated_and_missing_context_are_denied():
    client = APIClient()
    assert client.get("/api/v1/institutions/").status_code == 403

    user = User.objects.create_user(
        email="nocontext@example.com", password="StrongPass123!", is_active=True
    )
    grant_role(user, name="GlobalAdmin")
    client.force_login(user)

    response = client.get("/api/v1/institutions/")
    assert response.status_code == 403
    assert AuditLog.objects.filter(
        action="authz.denied", reason="missing_institution_context"
    ).exists()


@pytest.mark.django_db
def test_missing_active_role_is_denied_and_audited():
    institution = create_institution("norole")
    user = User.objects.create_user(
        email="norole@example.com",
        password="StrongPass123!",
        institution=institution,
        is_active=True,
    )
    client = APIClient()
    client.force_login(user)

    response = client.get("/api/v1/institutions/")
    assert response.status_code == 403
    assert AuditLog.objects.filter(
        action="authz.denied",
        reason="missing_active_institution_role",
        institution_id=institution.id,
    ).exists()


@pytest.mark.django_db
def test_institution_scope_filters_and_hides_other_institutions():
    inst_a = create_institution("alpha")
    inst_b = create_institution("beta")
    own_campus = Campus.objects.create(institution=inst_a, name="Alpha One", code="a1")
    other_campus = Campus.objects.create(institution=inst_b, name="Beta One", code="b1")

    user = User.objects.create_user(
        email="alpha@example.com", password="StrongPass123!", institution=inst_a
    )
    grant_role(user, inst_a)
    client = APIClient()
    client.force_login(user)

    listing = client.get("/api/v1/institutions/")
    assert listing.status_code == 200
    assert [item["id"] for item in listing.data["results"]] == [str(inst_a.id)]

    cross = client.get(f"/api/v1/institutions/{inst_b.id}/")
    assert cross.status_code == 404

    campuses = client.get("/api/v1/campuses/")
    assert campuses.status_code == 200
    assert all(item["institution_code"] == "alpha" for item in campuses.data["results"])

    assert client.get(f"/api/v1/campuses/{other_campus.id}/").status_code == 404
    assert client.get(f"/api/v1/campuses/{own_campus.id}/").status_code == 200


@pytest.mark.django_db
def test_campus_scope_hides_sibling_campus():
    institution = create_institution("gamma")
    own = Campus.objects.create(institution=institution, name="Main", code="main")
    sibling = Campus.objects.create(institution=institution, name="Annex", code="annex")

    user = User.objects.create_user(
        email="campus@example.com",
        password="StrongPass123!",
        institution=institution,
        campus=own,
    )
    grant_role(user, institution)
    client = APIClient()
    client.force_login(user)

    listing = client.get("/api/v1/campuses/")
    assert listing.status_code == 200
    assert [item["id"] for item in listing.data["results"]] == [str(own.id)]
    assert client.get(f"/api/v1/campuses/{sibling.id}/").status_code == 404


@pytest.mark.django_db
def test_global_role_and_superuser_bypass():
    inst_a = create_institution("delta")
    create_institution("epsilon")

    user = User.objects.create_user(
        email="global@example.com", password="StrongPass123!", institution=inst_a
    )
    grant_role(user, None, name="GlobalAdmin")
    client = APIClient()
    client.force_login(user)
    listing = client.get("/api/v1/institutions/")
    assert listing.status_code == 200, listing.data
    assert [item["id"] for item in listing.data["results"]] == [str(inst_a.id)]

    superuser = User.objects.create_superuser(
        email="root@example.com", password="StrongPass123!"
    )
    client.force_login(superuser)
    all_institutions = client.get("/api/v1/institutions/")
    assert all_institutions.status_code == 200
    assert len(all_institutions.data["results"]) == 2
