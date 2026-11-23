from django.db import transaction

from apps.audit.services import log_event

from .models import AcademicSession, Arm, ClassEnrolment, ClassLevel, Subject, SubjectOffering, Term


class AcademicWorkflowError(ValueError):
    pass


def _audit(actor, action, obj, **kwargs):
    log_event(
        action,
        actor=actor,
        target_type=type(obj).__name__,
        target_id=obj.pk,
        institution_id=getattr(obj, "institution_id", None),
        campus_id=getattr(obj, "campus_id", None),
        **kwargs,
    )


def create_session(actor, *, institution, campus=None, name, code, start_date, end_date):
    if end_date < start_date:
        raise AcademicWorkflowError("invalid_session_dates")
    session = AcademicSession.objects.create(
        institution=institution,
        campus=campus,
        name=name,
        code=code,
        start_date=start_date,
        end_date=end_date,
    )
    _audit(actor, "academics.session_created", session, change_summary={"code": code})
    return session


def close_session(actor, session):
    with transaction.atomic():
        locked = AcademicSession.objects.select_for_update().get(pk=session.pk)
        if locked.is_closed:
            raise AcademicWorkflowError("session_already_closed")
        locked.is_closed = True
        locked.save(update_fields=["is_closed", "updated_at"])
    _audit(actor, "academics.session_closed", locked)
    return locked


def create_term(actor, *, session, name, code, start_date, end_date):
    if not (session.start_date <= start_date <= end_date <= session.end_date):
        raise AcademicWorkflowError("term_outside_session")
    term = Term.objects.create(
        session=session, name=name, code=code, start_date=start_date, end_date=end_date
    )
    _audit(actor, "academics.term_created", term, change_summary={"code": code})
    return term


def create_class_level(actor, *, institution, campus=None, name, code, sequence=0):
    level = ClassLevel.objects.create(
        institution=institution, campus=campus, name=name, code=code, sequence=sequence
    )
    _audit(actor, "academics.class_level_created", level, change_summary={"code": code})
    return level


def create_arm(actor, *, class_level, name, code):
    arm = Arm.objects.create(class_level=class_level, name=name, code=code)
    _audit(actor, "academics.arm_created", arm, change_summary={"code": code})
    return arm


def create_subject(actor, *, institution, name, code):
    subject = Subject.objects.create(institution=institution, name=name, code=code)
    _audit(actor, "academics.subject_created", subject, change_summary={"code": code})
    return subject


def create_offering(
    actor, *, session, class_level, arm=None, subject, term=None, is_compulsory=True
):
    if (
        class_level.institution_id != session.institution_id
        or subject.institution_id != session.institution_id
    ):
        raise AcademicWorkflowError("cross_institution_offering")
    if arm and arm.class_level_id != class_level.id:
        raise AcademicWorkflowError("arm_class_mismatch")
    if term and term.session_id != session.id:
        raise AcademicWorkflowError("term_session_mismatch")
    offering = SubjectOffering.objects.create(
        session=session,
        term=term,
        class_level=class_level,
        arm=arm,
        subject=subject,
        is_compulsory=is_compulsory,
    )
    _audit(actor, "academics.offering_created", offering)
    return offering


def enrol_student(actor, *, session, class_level, arm, student):
    if (
        student.institution_id != session.institution_id
        or class_level.institution_id != session.institution_id
    ):
        raise AcademicWorkflowError("cross_institution_enrolment")
    if arm and arm.class_level_id != class_level.id:
        raise AcademicWorkflowError("arm_class_mismatch")
    enrolment = ClassEnrolment.objects.create(
        session=session, class_level=class_level, arm=arm, student=student
    )
    _audit(actor, "academics.student_enrolled", enrolment)
    return enrolment
