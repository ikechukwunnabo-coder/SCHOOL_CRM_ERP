import pytest
from django.core.management import call_command

from apps.core.tasks import celery_ping


def test_celery_ping():
    result = celery_ping.apply(throw=True)
    assert result.successful()
    assert result.get() == {"status": "ok"}


@pytest.mark.django_db
def test_verify_runtime_command():
    call_command("verify_runtime")
