from datetime import date

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.academics import services as academics_services
from apps.alumni.models import AlumniRecord
from apps.alumni.services import sync_alumni_record
from apps.permissions.models import Role, UserRole
from apps.students import services as student_services
from apps.students.models import Student


def create_user(username, institution, role_name):
    from apps.accounts.models import User

    user = User.objects.create_user(
        password="Testpass123!",
        email=f"{username}@example.com",
        institution=institution,
        is_staff=True,
    )
    role, _ = Role.objects.get_or_create(
        institution=institution,
        name=role_name,
        defaults={"is_system": False, "description": role_name},
    )
    UserRole.objects.create(
        user=user,
        role=role,
        scope_type=UserRole.ScopeType.INSTITUTION,
        scope_ref_id=institution.pk,
        is_active=True,
    )

    return user


class AlumniTests(TestCase):
    def setUp(self):
        from apps.institutions.models import Institution

        self.inst_a = Institution.objects.create(name="A", code="alma")
        self.inst_b = Institution.objects.create(name="B", code="almb")
        self.admin_a = create_user("alma-admin", self.inst_a, "Institution Administrator")
        self.admin_b = create_user("almb-admin", self.inst_b, "Institution Administrator")
        self.session_a = academics_services.create_session(
            self.admin_a,
            institution=self.inst_a,
            name="2026",
            code="2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        self.student_a = Student.objects.create(
            institution=self.inst_a,
            admission_number="ALM-A-001",
            first_name="A",
            last_name="Student",
            date_of_birth=date(2008, 1, 1),
            admission_date=date(2026, 1, 1),
            status=Student.LifecycleStatus.ACTIVE,
        )
        self.student_b = Student.objects.create(
            institution=self.inst_b,
            admission_number="ALM-B-001",
            first_name="B",
            last_name="Student",
            date_of_birth=date(2008, 1, 1),
            admission_date=date(2026, 1, 1),
            status=Student.LifecycleStatus.ACTIVE,
        )

    def test_graduation_creates_alumni_record_idempotently(self):
        student_services.change_lifecycle(
            self.admin_a,
            self.student_a,
            Student.LifecycleStatus.GRADUATED,
            effective_date=date(2026, 12, 31),
            reason="Completed",
        )
        record = AlumniRecord.objects.get(student=self.student_a)
        sync_alumni_record(
            actor=self.admin_a,
            student=self.student_a,
            event=record.graduation_event,
        )
        self.assertEqual(AlumniRecord.objects.filter(student=self.student_a).count(), 1)
        record.refresh_from_db()
        self.assertEqual(record.graduation_date.isoformat(), "2026-12-31")

    def test_alumni_api_read_only_and_scoped(self):
        student_services.change_lifecycle(
            self.admin_a,
            self.student_a,
            Student.LifecycleStatus.GRADUATED,
            effective_date=date(2026, 12, 31),
            reason="Completed",
        )
        student_services.change_lifecycle(
            self.admin_b,
            self.student_b,
            Student.LifecycleStatus.GRADUATED,
            effective_date=date(2026, 12, 31),
            reason="Completed",
        )
        client = APIClient()
        client.force_authenticate(self.admin_a)
        list_url = reverse("alumni-record-list")
        response = client.get(list_url)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        items = payload["results"] if "results" in payload else payload
        ids = {item["student"] for item in items}

        self.assertEqual(ids, {str(self.student_a.id)})
        record = AlumniRecord.objects.get(student=self.student_a)
        detail = reverse("alumni-record-detail", kwargs={"pk": record.pk})
        self.assertEqual(client.post(list_url, {}, format="json").status_code, 405)
        self.assertEqual(client.patch(detail, {}, format="json").status_code, 405)
        other = AlumniRecord.objects.get(student=self.student_b)
        other_url = reverse("alumni-record-detail", kwargs={"pk": other.pk})
        self.assertEqual(client.get(other_url).status_code, 404)
