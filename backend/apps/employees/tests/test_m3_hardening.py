import pytest

from apps.academics.tests.m3_helpers import (
    client_for,
    make_employee,
    make_school,
    make_user,
)
from apps.permissions.roles import HOD, SUBJECT_TEACHER


@pytest.mark.django_db
def test_employee_queryset_scope_and_role_checks():
    inst_a, campuses_a = make_school("empscopea", ("main", "annex"))
    inst_b, campuses_b = make_school("empscopeb", ("main",))
    admin_a = make_user("empscopea-admin", inst_a, campuses_a[0])
    admin_b = make_user("empscopeb-admin", inst_b, campuses_b[0])
    campus_user = make_user(
        "empscopea-campus", inst_a, campuses_a[0], role="Campus Administrator"
    )
    teacher = make_user("empscopea-teacher", inst_a, campuses_a[0], role=SUBJECT_TEACHER)
    hod = make_user("empscopea-hod", inst_a, campuses_a[0], role=HOD)

    own = make_employee(inst_a, campuses_a[0], "EMP-A-1")
    annex = make_employee(inst_a, campuses_a[1], "EMP-A-2")
    other = make_employee(inst_b, campuses_b[0], "EMP-B-1")

    client = client_for(admin_a)
    listing = client.get("/api/v1/employees/")
    assert listing.status_code == 200, listing.data
    visible = {item["id"] for item in listing.data["results"]}
    assert str(own.id) in visible
    assert str(annex.id) not in visible
    assert str(other.id) not in visible
    assert client.get(f"/api/v1/employees/{other.id}/").status_code == 404
    assert client.patch(f"/api/v1/employees/{other.id}/", {}, format="json").status_code == 404

    campus_client = client_for(campus_user)
    assert campus_client.get(f"/api/v1/employees/{annex.id}/").status_code == 404
    annex_url = f"/api/v1/employees/{annex.id}/"
    assert campus_client.patch(annex_url, {}, format="json").status_code == 404

    payload = {
        "institution": str(inst_a.id),
        "campus": str(campuses_a[0].id),
        "employee_number": "EMP-A-3",
        "first_name": "New",
        "last_name": "Employee",
    }
    assert client.post("/api/v1/employees/", payload, format="json").status_code == 201
    assert client.post(
        "/api/v1/employees/", {**payload, "institution": str(inst_b.id)}, format="json"
    ).status_code == 403

    teacher_client = client_for(teacher)
    assert teacher_client.get("/api/v1/employees/").status_code == 403
    hod_client = client_for(hod)
    assert hod_client.get("/api/v1/employees/").status_code == 200
    assert hod_client.post(
        "/api/v1/employees/", {**payload, "employee_number": "EMP-A-4"}, format="json"
    ).status_code == 403
    assert admin_b.institution_id == inst_b.id
