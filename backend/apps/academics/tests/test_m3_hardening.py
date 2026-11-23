import pytest

from apps.permissions.roles import SUBJECT_TEACHER

from .m3_helpers import client_for, make_school, make_structure, make_user

ENDPOINTS = (
    ("academic-sessions", "session"),
    ("terms", "term"),
    ("class-levels", "level"),
    ("arms", "arm"),
    ("subjects", "subject"),
    ("subject-offerings", "offering"),
    ("class-enrolments", "enrolment"),
)


@pytest.mark.django_db
@pytest.mark.parametrize("path,object_key", ENDPOINTS)
def test_academics_querysets_hide_cross_institution_and_cross_campus_objects(path, object_key):
    inst_a, campuses_a = make_school("acadscopea", ("main", "annex"))
    inst_b, campuses_b = make_school("acadscopeb", ("main",))
    admin_a = make_user("acadscopea-admin", inst_a, campuses_a[0])
    admin_b = make_user("acadscopeb-admin", inst_b, campuses_b[0])
    campus_user = make_user(
        "acadscopea-campus", inst_a, campuses_a[0], role="Campus Administrator"
    )
    struct_a = make_structure(admin_a, inst_a, campuses_a[0], "acad-a", student=True)
    struct_annex = make_structure(admin_a, inst_a, campuses_a[1], "acad-annex", student=True)
    struct_b = make_structure(admin_b, inst_b, campuses_b[0], "acad-b", student=True)

    client_a = client_for(admin_a)
    listing = client_a.get(f"/api/v1/{path}/")
    assert listing.status_code == 200, listing.data
    visible = {item["id"] for item in listing.data["results"]}
    assert str(struct_a[object_key].id) in visible
    assert str(struct_b[object_key].id) not in visible
    if object_key == "subject":
        assert str(struct_annex[object_key].id) in visible
    else:
        assert str(struct_annex[object_key].id) not in visible

    other_url = f"/api/v1/{path}/{struct_b[object_key].id}/"
    assert client_a.get(other_url).status_code == 404
    assert client_a.patch(other_url, {}, format="json").status_code == 404

    client_campus = client_for(campus_user)
    annex_url = f"/api/v1/{path}/{struct_annex[object_key].id}/"
    if object_key == "subject":
        assert client_campus.get(annex_url).status_code == 200
    else:
        assert client_campus.get(annex_url).status_code == 404
        assert client_campus.patch(annex_url, {}, format="json").status_code == 404
    assert client_campus.get(f"/api/v1/{path}/{struct_a[object_key].id}/").status_code == 200


@pytest.mark.django_db
def test_academics_create_payload_and_role_checks():
    inst_a, campuses_a = make_school("acadcreatea")
    inst_b, campuses_b = make_school("acadcreateb")
    admin_a = make_user("acadcreatea-admin", inst_a, campuses_a[0])
    teacher = make_user(
        "acadcreatea-teacher", inst_a, campuses_a[0], role=SUBJECT_TEACHER
    )
    make_school_admin_b = make_user("acadcreateb-admin", inst_b, campuses_b[0])

    valid_payload = {
        "institution": str(inst_a.id),
        "campus": str(campuses_a[0].id),
        "name": "Own Session",
        "code": "own-2026",
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
    }
    cross_payload = {**valid_payload, "institution": str(inst_b.id)}

    admin_client = client_for(admin_a)
    response = admin_client.post("/api/v1/academic-sessions/", valid_payload, format="json")
    assert response.status_code == 201, response.data
    response = admin_client.post("/api/v1/academic-sessions/", cross_payload, format="json")
    assert response.status_code == 403, response.data

    teacher_client = client_for(teacher)
    assert teacher_client.get("/api/v1/academic-sessions/").status_code == 200
    response = teacher_client.post("/api/v1/academic-sessions/", valid_payload, format="json")
    assert response.status_code == 403, response.data
    assert make_school_admin_b.institution_id == inst_b.id
