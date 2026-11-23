from datetime import date
from uuid import uuid4

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.academics import services as academics_services
from apps.examinations import services as examination_services
from apps.examinations.models import ResultRecord
from apps.permissions.models import Role, UserRole
from apps.students import services as student_services
from apps.students.models import Student

from .. import services
from ..models import Transcript, TranscriptKind, TranscriptVerification

ADMIN_ROLE = "Institution Administrator"
REGISTRAR_ROLE = "Registrar/Admissions"
EXAM_ROLE = "Examination Officer"
PRINCIPAL_ROLE = "Principal/VP"
TEACHER_ROLE = "Teacher"


def create_user(username, institution, role_names):
    from apps.accounts.models import User

    user = User.objects.create_user(
        password="Testpass123!",
        email=f"{username}-{uuid4().hex[:6]}@example.com",
        institution=institution,
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


def build_context(*, complete=True):
    from apps.institutions.models import Institution

    institution = Institution.objects.create(
        name="Transcript Institution",
        code=f"TRST-{uuid4().hex[:6].upper()}",
    )
    admin = create_user("tr-admin", institution, [ADMIN_ROLE])
    registrar = create_user("tr-registrar", institution, [REGISTRAR_ROLE])
    exam = create_user("tr-exam", institution, [EXAM_ROLE])
    principal = create_user("tr-principal", institution, [PRINCIPAL_ROLE])
    teacher = create_user("tr-teacher", institution, [TEACHER_ROLE])
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
        name="Grade 12",
        code="G12",
        sequence=12,
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
        admission_number="TR-STU-001",
        first_name="Ada",
        last_name="Okafor",
        date_of_birth=date(2008, 5, 1),
        admission_date=date(2026, 1, 1),
        status=Student.LifecycleStatus.ACTIVE,
    )
    academics_services.enrol_student(
        admin,
        session=session,
        class_level=class_level,
        arm=arm,
        student=student,
    )
    scheme = examination_services.create_scheme(
        admin,
        institution=institution,
        session=session,
        term=term,
        class_level=class_level,
        arm=arm,
        name="Final Assessment",
        code="FINAL-2026-G12",
        effective_from=date(2026, 1, 1),
    )
    examination_services.add_component(
        admin,
        scheme=scheme,
        code="CA",
        name="Continuous Assessment",
        max_marks=100,
        weight=40,
        sequence=1,
    )
    examination_services.add_component(
        admin,
        scheme=scheme,
        code="EXAM",
        name="Examination",
        max_marks=100,
        weight=60,
        sequence=2,
    )
    scale = examination_services.create_grading_scale(
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
    if complete:
        ResultRecord.objects.create(
            institution=institution,
            student=student,
            offering=offering,
            scheme=scheme,
            grading_scale=scale,
            session=session,
            term=term,
            component_scores={"CA": 80, "EXAM": 90},
            total_score=86,
            grade="A",
            remark="Excellent",
            status=ResultRecord.Status.PUBLISHED,
            published_by=exam,
            published_at=timezone.now(),
        )
        student_services.change_lifecycle(
            admin,
            student,
            Student.LifecycleStatus.GRADUATED,
            effective_date=date(2026, 12, 31),
            reason="Completed final examinations",
        )
    return {
        "institution": institution,
        "admin": admin,
        "registrar": registrar,
        "exam": exam,
        "principal": principal,
        "teacher": teacher,
        "session": session,
        "term": term,
        "student": student,
        "scale": scale,
    }


def approved_request(ctx, *, requested_kind=TranscriptKind.OFFICIAL):
    request_obj = services.request_transcript(
        ctx["registrar"],
        student=ctx["student"],
        purpose="Employment verification",
        requested_kind=requested_kind,
    )
    return services.approve_transcript_request(ctx["exam"], request=request_obj)


class TranscriptServiceTests(TestCase):
    def setUp(self):
        self.ctx = build_context()

    def test_transcript_generation_issuance_and_verification(self):
        request_obj = approved_request(self.ctx)
        transcript, raw_token = services.generate_transcript(
            self.ctx["registrar"], request=request_obj
        )
        self.assertEqual(transcript.version, 1)
        self.assertEqual(transcript.kind, TranscriptKind.OFFICIAL)
        self.assertEqual(transcript.status, Transcript.Status.GENERATED)
        self.assertTrue(transcript.file.read().startswith(b"%PDF"))
        self.assertEqual(transcript.results_snapshot[0]["grade"], "A")
        self.assertTrue(transcript.completeness["is_complete"])
        self.ctx["scale"].grades = [
            {"min": 0, "max": 100, "grade": "X", "remark": "Changed"}
        ]
        self.ctx["scale"].save()
        transcript.refresh_from_db()
        self.assertEqual(transcript.results_snapshot[0]["grading_scale"]["code"], "STD")
        issued = services.issue_transcript(
            self.ctx["registrar"],
            transcript=transcript,
            issued_to="Example Employer",
            purpose="Employment verification",
        )
        self.assertEqual(issued.status, Transcript.Status.ISSUED)
        verification = services.verify_transcript(raw_token)
        self.assertTrue(verification["valid"])
        self.assertEqual(verification["reference_number"], transcript.reference_number)
        self.assertNotIn("student", verification)
        self.assertEqual(
            TranscriptVerification.objects.filter(
                transcript=transcript,
                outcome=TranscriptVerification.Outcome.VALID,
            ).count(),
            1,
        )

    def test_official_generation_requires_complete_record(self):
        ctx = build_context(complete=False)
        request_obj = approved_request(ctx)
        with self.assertRaises(services.TranscriptError) as error:
            services.generate_transcript(ctx["registrar"], request=request_obj)
        self.assertEqual(str(error.exception), "official_transcript_requires_complete_record")
        provisional_request = approved_request(
            ctx, requested_kind=TranscriptKind.PROVISIONAL
        )
        transcript, _ = services.generate_transcript(
            ctx["registrar"], request=provisional_request
        )
        self.assertEqual(transcript.kind, TranscriptKind.PROVISIONAL)
        self.assertFalse(transcript.completeness["is_complete"])

    def test_correction_supersedes_old_version_and_token(self):
        request_obj = approved_request(self.ctx)
        transcript, old_token = services.generate_transcript(
            self.ctx["registrar"], request=request_obj
        )
        services.issue_transcript(
            self.ctx["registrar"],
            transcript=transcript,
            issued_to="Example Employer",
            purpose="Employment verification",
        )
        corrected, new_token = services.correct_transcript(
            self.ctx["registrar"],
            transcript=transcript,
            reason="Correct employer name",
            issued_to="Example Employer Ltd",
            purpose="Employment verification",
        )
        transcript.refresh_from_db()
        self.assertEqual(transcript.status, Transcript.Status.SUPERSEDED)
        self.assertEqual(corrected.version, 2)
        self.assertEqual(corrected.supersedes_id, transcript.pk)
        self.assertEqual(
            services.verify_transcript(old_token)["status"],
            TranscriptVerification.Outcome.SUPERSEDED,
        )
        self.assertEqual(
            services.verify_transcript(new_token)["status"],
            TranscriptVerification.Outcome.INVALID_STATE,
        )
        services.issue_transcript(
            self.ctx["registrar"],
            transcript=corrected,
            issued_to="Example Employer Ltd",
            purpose="Employment verification",
        )
        self.assertTrue(services.verify_transcript(new_token)["valid"])
        self.assertEqual(transcript.events.count(), 3)

    def test_revocation_invalidates_verification(self):
        request_obj = approved_request(self.ctx)
        transcript, raw_token = services.generate_transcript(
            self.ctx["registrar"], request=request_obj
        )
        services.issue_transcript(
            self.ctx["registrar"],
            transcript=transcript,
            issued_to="Example Employer",
            purpose="Employment verification",
        )
        services.revoke_transcript(
            self.ctx["registrar"],
            transcript=transcript,
            reason="Issued in error",
        )
        self.assertEqual(
            services.verify_transcript(raw_token)["status"],
            TranscriptVerification.Outcome.REVOKED,
        )


class TranscriptApiPermissionTests(TestCase):
    def setUp(self):
        self.ctx = build_context()
        self.client = APIClient()

    def test_api_workflow_permissions_public_verification_and_download(self):
        self.client.force_authenticate(self.ctx["registrar"])
        response = self.client.post(
            reverse("transcript-request-list"),
            {
                "student": str(self.ctx["student"].id),
                "purpose": "Employment verification",
                "requested_kind": TranscriptKind.OFFICIAL,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        request_id = response.data["id"]
        self.client.force_authenticate(self.ctx["teacher"])
        denied = self.client.post(
            reverse("transcript-request-list"),
            {"student": str(self.ctx["student"].id), "purpose": "Employment verification"},
            format="json",
        )
        self.assertEqual(denied.status_code, 403)
        self.client.force_authenticate(self.ctx["exam"])
        approved = self.client.post(
            reverse("transcript-request-approve", kwargs={"pk": request_id}),
            {},
            format="json",
        )
        self.assertEqual(approved.status_code, 200)
        self.client.force_authenticate(self.ctx["registrar"])
        generated = self.client.post(
            reverse("transcript-request-generate", kwargs={"pk": request_id}),
            {},
            format="json",
        )
        self.assertEqual(generated.status_code, 201)
        transcript_id = generated.data["id"]
        raw_token = generated.data["verification_token"]
        public_client = APIClient()
        verified = public_client.post(
            reverse("transcript-verify"),
            {"token": raw_token},
            format="json",
        )
        self.assertEqual(verified.status_code, 200)
        self.assertFalse(verified.data["valid"])
        issued = self.client.post(
            reverse("transcript-issue", kwargs={"pk": transcript_id}),
            {"issued_to": "Example Employer", "purpose": "Employment verification"},
            format="json",
        )
        self.assertEqual(issued.status_code, 200)
        verified = public_client.post(
            reverse("transcript-verify"),
            {"token": raw_token},
            format="json",
        )
        self.assertTrue(verified.data["valid"])
        self.client.force_authenticate(self.ctx["teacher"])
        forbidden = self.client.get(
            reverse("transcript-download", kwargs={"pk": transcript_id})
        )
        self.assertEqual(forbidden.status_code, 403)
        self.client.force_authenticate(self.ctx["registrar"])
        downloaded = self.client.get(
            reverse("transcript-download", kwargs={"pk": transcript_id})
        )
        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(downloaded["Content-Type"], "application/pdf")
        self.assertTrue(b"".join(downloaded.streaming_content).startswith(b"%PDF"))
