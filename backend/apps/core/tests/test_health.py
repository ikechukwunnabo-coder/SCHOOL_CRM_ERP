import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_health_endpoint():
    client = APIClient()
    resp = client.get("/api/v1/health/")
    assert resp.status_code == 200
    assert "status" in resp.data
    assert "database" in resp.data
