from datetime import date

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.academics import services as academics_services
from apps.employees.models import Employee
from apps.permissions.models import Role, UserRole
from apps.teaching import services as teaching_services
from apps.teaching.models import TeacherAssignment

from .. import services
from ..models import ResultCorrection, ResultRecord

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


def build_context():
    from apps.institutions.models import Institution
    from apps.students.models import Student

    institution = Institution.objects.create(
        name="Test Institution",
        code="test-m4",
    )
    admin = create_user("m4-admin", institution, [ADMIN_ROLE])
    teacher_user = create_user("m4-teacher", institution, [TEACHER_ROLE])
    exam_user = create_user("m4-exam", institution, [EXAM_ROLE])
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
        admin,
        institution=institution,
        name="Grade 10",
        code="G10",
        sequence=10,
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
        admission_number="M4-STU-001",
        first_name="Ada",
        last_name="Okafor",
        date_of_birth=date(2010, 5, 1),
        admission_date=date(2026, 1, 1),
    )
    academics_services.enrol_student(
        admin,
        session=session,
        class_level=class_level,
        arm=arm,
        student=student,
    )
    employee = Employee.objects.create(
        institution=institution,
        user=teacher_user,
        employee_number="M4-EMP-001",
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
        name="First Term Assessment",
        code="FT-2026-G10",
        effective_from=date(2026, 1, 1),
    )
    services.add_component(
        admin,
        scheme=scheme,
        code="CA",
        name="Continuous Assessment",
        max_marks=100,
        weight=40,
        sequence=1,
    )
    services.add_component(
        admin,
        scheme=scheme,
        code="EXAM",
        name="Examination",
        max_marks=100,
        weight=60,
        sequence=2,
    )
    services.create_grading_scale(
        admin,
        institution=institution,
        name="Standard Grades",
        code="STD",
        effective_from=date(2026, 1, 1),
        pass_mark=50,
        grades=[
            {"min": 70, "max": 100, "grade": "A", "remark": "Excellent"},
            {"min": 50, "max": 69.99, "grade": "B", "remark": "Good"},
            {"min": 0, "max": 49.99, "grade": "F", "remark": "Fail"},
        ],
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
    }


class ExaminationsServiceTests(TestCase):
    def setUp(self):
        self.ctx = build_context()

    def test_full_result_workflow_and_report_card(self):
        result = services.record_result(
            self.ctx["teacher"],
            scheme=self.ctx["scheme"],
            offering=self.ctx["offering"],
            student=self.ctx["student"],
            component_scores={"CA": 80, "EXAM": 90},
        )
        self.assertEqual(result.total_score, 86.0)
        self.assertEqual(result.grade, "A")
        submitted = services.submit_results(
            self.ctx["teacher"],
            scheme=self.ctx["scheme"],
            offering=self.ctx["offering"],
        )
        self.assertEqual(submitted, 1)
        result.refresh_from_db()
        self.assertEqual(result.status, ResultRecord.Status.SUBMITTED)
        services.approve_result(self.ctx["exam"], result=result)
        services.publish_result(self.ctx["exam"], result=result)
        card = services.generate_report_card(
            self.ctx["exam"],
            student=self.ctx["student"],
            session=self.ctx["session"],
            term=self.ctx["term"],
        )
        self.assertEqual(card.version, 1)
        self.assertEqual(card.results_snapshot[0]["grade"], "A")
        self.assertEqual(result.workflow_actions.count(), 3)

    def test_self_approval_and_unassigned_teacher_are_denied(self):
        result = services.record_result(
            self.ctx["teacher"],
            scheme=self.ctx["scheme"],
            offering=self.ctx["offering"],
            student=self.ctx["student"],
            component_scores={"CA": 80, "EXAM": 90},
        )
        services.submit_results(
            self.ctx["teacher"],
            scheme=self.ctx["scheme"],
            offering=self.ctx["offering"],
        )
        result.refresh_from_db()
        with self.assertRaises(services.ExaminationError) as error:
            services.approve_result(self.ctx["teacher"], result=result)
        self.assertEqual(str(error.exception), "self_approval_not_permitted")
        other = create_user("m4-other-teacher", self.ctx["institution"], [TEACHER_ROLE])
        with self.assertRaises(services.ExaminationError) as error:
            services.record_result(
                other,
                scheme=self.ctx["scheme"],
                offering=self.ctx["offering"],
                student=self.ctx["student"],
                component_scores={"CA": 80, "EXAM": 90},
            )
        self.assertEqual(str(error.exception), "teacher_not_assigned_to_offering")

    def test_post_publication_correction_preserves_history(self):
        result = services.record_result(
            self.ctx["teacher"],
            scheme=self.ctx["scheme"],
            offering=self.ctx["offering"],
            student=self.ctx["student"],
            component_scores={"CA": 80, "EXAM": 90},
        )
        services.submit_results(
            self.ctx["teacher"],
            scheme=self.ctx["scheme"],
            offering=self.ctx["offering"],
        )
        result.refresh_from_db()
        services.approve_result(self.ctx["exam"], result=result)
        services.publish_result(self.ctx["exam"], result=result)
        services.correct_result(
            self.ctx["exam"],
            result=result,
            component_scores={"CA": 90, "EXAM": 95},
            reason="Clerical correction",
        )
        result.refresh_from_db()
        self.assertEqual(result.correction_count, 1)
        self.assertEqual(result.status, ResultRecord.Status.SUBMITTED)
        self.assertEqual(ResultCorrection.objects.filter(result=result).count(), 1)
        with self.assertRaises(services.ExaminationError) as error:
            services.generate_report_card(
                self.ctx["exam"],
                student=self.ctx["student"],
                session=self.ctx["session"],
                term=self.ctx["term"],
            )
        self.assertEqual(str(error.exception), "no_published_results")


class ExaminationsApiPermissionTests(TestCase):
    def setUp(self):
        self.ctx = build_context()
        self.client = APIClient()
        self.result = services.record_result(
            self.ctx["teacher"],
            scheme=self.ctx["scheme"],
            offering=self.ctx["offering"],
            student=self.ctx["student"],
            component_scores={"CA": 80, "EXAM": 90},
        )
        services.submit_results(
            self.ctx["teacher"],
            scheme=self.ctx["scheme"],
            offering=self.ctx["offering"],
        )
        self.result.refresh_from_db()

    def test_teacher_cannot_approve_or_publish(self):
        self.client.force_authenticate(self.ctx["teacher"])
        approve_url = reverse("examinations:result-approve", kwargs={"pk": self.result.pk})
        response = self.client.post(approve_url, {}, format="json")
        self.assertEqual(response.status_code, 403)
        publish_url = reverse("examinations:result-publish", kwargs={"pk": self.result.pk})
        response = self.client.post(publish_url, {}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_examination_officer_can_approve_and_publish(self):
        self.client.force_authenticate(self.ctx["exam"])
        approve_url = reverse("examinations:result-approve", kwargs={"pk": self.result.pk})
        response = self.client.post(approve_url, {}, format="json")
        self.assertEqual(response.status_code, 200)
        publish_url = reverse("examinations:result-publish", kwargs={"pk": self.result.pk})
        response = self.client.post(publish_url, {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.result.refresh_from_db()
        self.assertEqual(self.result.status, ResultRecord.Status.PUBLISHED)
