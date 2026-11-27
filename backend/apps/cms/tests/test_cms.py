import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.cms.models import CmsPage
from apps.permissions.models import Role, UserRole
from apps.permissions.roles import PARENT_GUARDIAN, SUPER_ADMIN


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def base(db):
    from apps.institutions.models import Campus, Institution

    inst = Institution.objects.create(code="CMS", name="CMS Inst")
    campus = Campus.objects.create(institution=inst, code="MAIN", name="Main")
    User = get_user_model()
    admin = User.objects.create_user(
        email="cms-admin@test.com", password="pass12345", institution=inst, campus=campus
    )
    parent = User.objects.create_user(
        email="cms-parent@test.com", password="pass12345", institution=inst, campus=campus
    )
    Role.objects.get_or_create(name=SUPER_ADMIN, defaults={"is_system": True})
    Role.objects.get_or_create(name=PARENT_GUARDIAN, defaults={"is_system": True})
    UserRole.objects.create(user=admin, role=Role.objects.get(name=SUPER_ADMIN))
    UserRole.objects.create(user=parent, role=Role.objects.get(name=PARENT_GUARDIAN))
    return inst, admin, parent


@pytest.mark.django_db
def test_cms_page_create_denies_parent(api_client, base):
    inst, _, parent = base
    api_client.force_authenticate(parent)
    r = api_client.post(
        "/api/v1/cms/pages/",
        {"institution": str(inst.id), "slug": "home", "title": "Home"},
        format="json",
    )
    assert r.status_code in {403, 404}


@pytest.mark.django_db
def test_cms_page_create_allows_admin(api_client, base):
    inst, admin, _ = base
    api_client.force_authenticate(admin)
    r = api_client.post(
        "/api/v1/cms/pages/",
        {"institution": str(inst.id), "slug": "home", "title": "Home", "status": "draft"},
        format="json",
    )
    assert r.status_code == 201


@pytest.mark.django_db
def test_public_cms_pages_only_published(api_client, base):
    inst, _, _ = base
    CmsPage.objects.create(
        institution=inst, slug="draft", title="Draft", status=CmsPage.Status.DRAFT
    )
    CmsPage.objects.create(
        institution=inst,
        slug="pub",
        title="Pub",
        status=CmsPage.Status.PUBLISHED,
        is_public=True,
    )
    r = api_client.get(f"/api/v1/cms/public/pages/?institution={inst.id}")
    assert r.status_code == 200
    slugs = [p["slug"] for p in r.data]
    assert "pub" in slugs
    assert "draft" not in slugs
