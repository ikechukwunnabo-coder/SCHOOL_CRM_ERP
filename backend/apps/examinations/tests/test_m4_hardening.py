from datetime import date

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.academics import services as academics_services
from apps.employees.models import Employee
from apps.permissions.models import Role, UserRole
from apps.students.models import Student
from apps.teaching import services as teaching_services
from apps.teaching.models import TeacherAssignment

from .. import services
from ..models import GradingPolicy, ResultRecord

ADMIN_ROLE = "Institution Administrator"
TEACHER_ROLE = "Teacher"
EXAM_ROLE = "Examination Officer"


def create_user(username, institution, role_names, campus=None):
    from apps.accounts.models import User

    user = User.objects.create_user(
        password="Testpass123!",
        email=f"{username}@example.com",
        institution=institution,
        campus=campus,
        is_staff=True,
    )
    for role_name in role_names:
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


def build_context(code="m4h"):
    from apps.institutions.models import Institution

    institution = Institution.objects.create(name=f"Inst {code}", code=code)
    admin = create_user(f"{code}-admin", institution, [ADMIN_ROLE])
    teacher_user = create_user(f"{code}-teacher", institution, [TEACHER_ROLE])
    exam_user = create_user(f"{code}-exam", institution, [EXAM_ROLE])
    session = academics_services.create_session(
        admin,
        institution=institution,
        name="2026 Session",
        code="2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    term = academics_services.create_term(
        admin,
        session=session,
        name="First Term",
        code="T1",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 6, 30),
    )
    class_level = academics_services.create_class_level(
        admin, institution=institution, name="Grade 10", code="G10", sequence=10
    )
    arm = academics_services.create_arm(admin, class_level=class_level, name="Gold", code="G")
    subject = academics_services.create_subject(
        admin, institution=institution, name="Mathematics", code="MATH"
    )
    offering = academics_services.create_offering(
        admin,
        session=session,
        term=term,
        class_level=class_level,
        arm=arm,
        subject=subject,
    )
    student = Student.objects.create(
        institution=institution,
        admission_number=f"{code.upper()}-001",
        first_name="Ada",
        last_name="Okafor",
        date_of_birth=date(2010, 5, 1),
        admission_date=date(2026, 1, 1),
    )
    academics_services.enrol_student(
        admin, session=session, class_level=class_level, arm=arm, student=student
    )
    employee = Employee.objects.create(
        institution=institution,
        user=teacher_user,
        employee_number=f"{code.upper()}-EMP",
        first_name="Chidi",
        last_name="Teacher",
        status=Employee.Status.ACTIVE,
    )
    teaching_services.assign_teacher(
        admin,
        offering=offering,
        employee=employee,
        role=TeacherAssignment.Role.LEAD,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    scheme = services.create_scheme(
        admin,
        institution=institution,
        session=session,
        term=term,
        class_level=class_level,
        arm=arm,
        name="Scheme",
        code="SCH",
        effective_from=date(2026, 1, 1),
    )
    services.add_component(
        admin, scheme=scheme, code="CA", name="CA", max_marks=100, weight=40, sequence=1
    )
    services.add_component(
        admin, scheme=scheme, code="EXAM", name="Exam", max_marks=100, weight=60, sequence=2
    )
    scale = services.create_grading_scale(
        admin,
        institution=institution,
        name="Standard",
        code="STD",
        effective_from=date(2026, 1, 1),
        pass_mark=50,
        grades=[
            {"min": 70, "max": 100, "grade": "A", "remark": "Excellent"},
            {"min": 50, "max": 69.99, "grade": "B", "remark": "Good"},
            {"min": 0, "max": 49.99, "grade": "F", "remark": "Fail"},
        ],
    )
    policy = services.create_grading_policy(
        admin,
        institution=institution,
        grading_scale=scale,
        name="Default Policy",
        code="POL",
        effective_from=date(2026, 1, 1),
    )
    return {
        "institution": institution,
        "admin": admin,
        "teacher": teacher_user,
        "exam": exam_user,
        "session": session,
        "term": term,
        "offering": offering,
        "student": student,
        "scheme": scheme,
        "scale": scale,
        "policy": policy,
    }


class ReportCardPdfTests(TestCase):
    def setUp(self):
        self.ctx = build_context("rcpdf")

    def test_report_card_generation_requires_published_results_and_stores_pdf(self):
        result = services.record_result(
            self.ctx["teacher"],
            scheme=self.ctx["scheme"],
            offering=self.ctx["offering"],
            student=self.ctx["student"],
            component_scores={"CA": 80, "EXAM": 90},
        )
        with self.assertRaises(services.ExaminationError) as err:
            services.generate_report_card(
                self.ctx["exam"],
                student=self.ctx["student"],
                session=self.ctx["session"],
                term=self.ctx["term"],
            )
        self.assertEqual(str(err.exception), "no_published_results")
        services.submit_results(
            self.ctx["teacher"], scheme=self.ctx["scheme"], offering=self.ctx["offering"]
        )
        result.refresh_from_db()
        services.approve_result(self.ctx["exam"], result=result)
        services.publish_result(self.ctx["exam"], result=result)
        card = services.generate_report_card(
            self.ctx["exam"],
            student=self.ctx["student"],
            session=self.ctx["session"],
            term=self.ctx["term"],
        )
        self.assertTrue(card.file_ref)
        self.assertEqual(card.content_type, "application/pdf")
        self.assertGreater(card.size_bytes, 0)
        self.assertEqual(len(card.pdf_sha256), 64)
        self.assertTrue(card.file.read().startswith(b"%PDF"))
        self.assertEqual(card.document_snapshot["results"][0]["grade"], "A")


class WorkflowBypassTests(TestCase):
    def setUp(self):
        self.ctx = build_context("bypass")
        self.client = APIClient()
        self.result = services.record_result(
            self.ctx["teacher"],
            scheme=self.ctx["scheme"],
            offering=self.ctx["offering"],
            student=self.ctx["student"],
            component_scores={"CA": 80, "EXAM": 90},
        )

    def test_manual_result_recording_endpoint(self):
        self.client.force_authenticate(self.ctx["teacher"])
        url = reverse("examinations:result-list")
        response = self.client.post(
            url,
            {
                "scheme": str(self.ctx["scheme"].id),
                "offering": str(self.ctx["offering"].id),
                "student": str(self.ctx["student"].id),
                "component_scores": {"CA": 70, "EXAM": 80},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], ResultRecord.Status.DRAFT)

    def test_generic_writes_blocked_for_results_and_report_cards(self):
        self.client.force_authenticate(self.ctx["exam"])
        result_url = reverse("examinations:result-detail", kwargs={"pk": self.result.pk})
        patch_response = self.client.patch(result_url, {"grade": "Z"}, format="json")
        self.assertEqual(patch_response.status_code, 405)
        self.assertEqual(self.client.put(result_url, {}, format="json").status_code, 405)
        self.assertEqual(self.client.delete(result_url).status_code, 405)
        services.submit_results(
            self.ctx["teacher"], scheme=self.ctx["scheme"], offering=self.ctx["offering"]
        )

        self.result.refresh_from_db()
        services.approve_result(self.ctx["exam"], result=self.result)
        services.publish_result(self.ctx["exam"], result=self.result)
        card = services.generate_report_card(
            self.ctx["exam"],
            student=self.ctx["student"],
            session=self.ctx["session"],
            term=self.ctx["term"],
        )
        card_url = reverse("examinations:report-card-detail", kwargs={"pk": card.pk})
        card_patch = self.client.patch(card_url, {"reference": "X"}, format="json")
        self.assertEqual(card_patch.status_code, 405)
        self.assertEqual(self.client.delete(card_url).status_code, 405)
        card_create = self.client.post(reverse("examinations:report-card-list"), {}, format="json")
        self.assertEqual(card_create.status_code, 405)



class GradingPolicyTests(TestCase):
    def setUp(self):
        self.ctx = build_context("policy")

    def test_select_grading_scale_prefers_effective_policy(self):
        scale2 = services.create_grading_scale(
            self.ctx["admin"],
            institution=self.ctx["institution"],
            name="Policy Scale",
            code="POLICY",
            effective_from=date(2026, 1, 1),
            pass_mark=60,
            grades=[
                {"min": 60, "max": 100, "grade": "P", "remark": "Pass"},
                {"min": 0, "max": 59.99, "grade": "F", "remark": "Fail"},
            ],
        )
        services.create_grading_policy(
            self.ctx["admin"],
            institution=self.ctx["institution"],
            grading_scale=scale2,
            name="Strict",
            code="STRICT",
            effective_from=date(2026, 2, 1),
        )
        selected = services.select_grading_scale(
            institution_id=self.ctx["institution"].id, as_of=date(2026, 3, 1)
        )
        self.assertEqual(selected.code, "POLICY")
        policies = GradingPolicy.objects.filter(institution=self.ctx["institution"])
        self.assertEqual(policies.count(), 2)



class ScopeAndIdorTests(TestCase):
    def setUp(self):
        self.a = build_context("ida")
        self.b = build_context("idb")
        self.client = APIClient()

    def test_cross_institution_idor_denied(self):
        result = services.record_result(
            self.b["teacher"],
            scheme=self.b["scheme"],
            offering=self.b["offering"],
            student=self.b["student"],
            component_scores={"CA": 80, "EXAM": 90},
        )
        self.client.force_authenticate(self.a["exam"])
        url = reverse("examinations:result-detail", kwargs={"pk": result.pk})
        self.assertEqual(self.client.get(url).status_code, 404)
        approve = reverse("examinations:result-approve", kwargs={"pk": result.pk})
        self.assertEqual(self.client.post(approve, {}, format="json").status_code, 404)

    def test_report_card_download_scoped_and_requires_published(self):
        result = services.record_result(
            self.a["teacher"],
            scheme=self.a["scheme"],
            offering=self.a["offering"],
            student=self.a["student"],
            component_scores={"CA": 80, "EXAM": 90},
        )
        services.submit_results(
            self.a["teacher"], scheme=self.a["scheme"], offering=self.a["offering"]
        )

        result.refresh_from_db()
        services.approve_result(self.a["exam"], result=result)
        services.publish_result(self.a["exam"], result=result)
        card = services.generate_report_card(
            self.a["exam"],
            student=self.a["student"],
            session=self.a["session"],
            term=self.a["term"],
        )

        self.client.force_authenticate(self.b["exam"])
        dl = reverse("examinations:report-card-download", kwargs={"pk": card.pk})
        self.assertEqual(self.client.get(dl).status_code, 404)
        self.client.force_authenticate(self.a["exam"])
        response = self.client.get(dl)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
