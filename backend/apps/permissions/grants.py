from apps.admissions.permissions import (
    ADMISSION_DECIDE_ROLES,
    ADMISSION_MANAGE_ROLES,
    ADMISSION_VIEW_ROLES,
)
from apps.students.permissions import STUDENT_MANAGE_ROLES, STUDENT_VIEW_ROLES

from .roles import (
    ADMIN_ROLES,
    CLASS_TEACHER,
    EXAM_OFFICER,
    HOD,
    HR_OFFICER,
    PRINCIPAL,
    REGISTRAR,
    SUBJECT_TEACHER,
    VICE_PRINCIPAL,
)

TEACHING_VIEW_ROLES = (HOD, CLASS_TEACHER, SUBJECT_TEACHER, PRINCIPAL, VICE_PRINCIPAL)
LEADERSHIP_REVIEW_ROLES = (HOD, PRINCIPAL, VICE_PRINCIPAL)
EXAMINATION_MANAGE_ROLES = (HOD, SUBJECT_TEACHER, EXAM_OFFICER, PRINCIPAL)

VERBS = (
    "view",
    "create",
    "update",
    "delete_or_archive",
    "submit",
    "review",
    "approve",
    "publish",
    "export",
    "print",
    "reverse_or_refund",
    "issue_or_revoke",
    "upload",
    "download",
    "import",
)

MODULE_GRANTS = {
    "admissions": {
        "view": ADMISSION_VIEW_ROLES,
        "create": ADMISSION_MANAGE_ROLES,
        "update": ADMISSION_MANAGE_ROLES,
        "delete_or_archive": ADMISSION_MANAGE_ROLES,
        "submit": ADMISSION_MANAGE_ROLES,
        "review": ADMISSION_MANAGE_ROLES,
        "approve": ADMISSION_DECIDE_ROLES,
        "export": ADMIN_ROLES,
        "print": ADMISSION_VIEW_ROLES,
    },
    "students": {
        "view": STUDENT_VIEW_ROLES,
        "create": ADMIN_ROLES + (REGISTRAR,),
        "update": STUDENT_MANAGE_ROLES,
        "delete_or_archive": ADMIN_ROLES,
        "export": ADMIN_ROLES,
        "print": STUDENT_VIEW_ROLES,
    },
    "documents": {
        "view": ADMISSION_VIEW_ROLES,
        "upload": ADMISSION_MANAGE_ROLES,
        "download": ADMISSION_VIEW_ROLES,
        "delete_or_archive": ADMIN_ROLES,
    },
    "imports": {
        "view": ADMIN_ROLES + (REGISTRAR,),
        "create": ADMIN_ROLES + (REGISTRAR,),
        "approve": ADMIN_ROLES,
        "import": ADMIN_ROLES + (REGISTRAR,),
        "export": ADMIN_ROLES,
    },
    "employees": {
        "view": ADMIN_ROLES + (REGISTRAR, HOD, HR_OFFICER, PRINCIPAL),
        "create": ADMIN_ROLES + (REGISTRAR, HR_OFFICER),
        "update": ADMIN_ROLES + (REGISTRAR, HR_OFFICER),
        "delete_or_archive": ADMIN_ROLES,
        "export": ADMIN_ROLES + (HR_OFFICER,),
    },
    "academics": {
        "view": ADMIN_ROLES + (REGISTRAR, *TEACHING_VIEW_ROLES),
        "create": ADMIN_ROLES + (REGISTRAR, HOD, PRINCIPAL),
        "update": ADMIN_ROLES + (REGISTRAR, HOD, PRINCIPAL),
        "delete_or_archive": ADMIN_ROLES,
        "publish": ADMIN_ROLES + (HOD, PRINCIPAL),
        "export": ADMIN_ROLES + (REGISTRAR, HOD),
    },
    "teaching": {
        "view": ADMIN_ROLES + (REGISTRAR, *TEACHING_VIEW_ROLES),
        "create": ADMIN_ROLES + (REGISTRAR, HOD, PRINCIPAL),
        "update": ADMIN_ROLES + (HOD, PRINCIPAL),
        "delete_or_archive": ADMIN_ROLES,
        "publish": ADMIN_ROLES + (HOD, PRINCIPAL),
        "approve": ADMIN_ROLES + LEADERSHIP_REVIEW_ROLES,
        "export": ADMIN_ROLES + (REGISTRAR, HOD),
    },
    "attendance": {
        "view": ADMIN_ROLES + (REGISTRAR, *TEACHING_VIEW_ROLES),
        "create": ADMIN_ROLES + (REGISTRAR, HOD, CLASS_TEACHER, SUBJECT_TEACHER),
        "update": ADMIN_ROLES + (HOD, CLASS_TEACHER, SUBJECT_TEACHER),
        "delete_or_archive": ADMIN_ROLES,
        "approve": ADMIN_ROLES + (HOD, PRINCIPAL),
        "export": ADMIN_ROLES + (REGISTRAR, HOD),
        "print": ADMIN_ROLES + (REGISTRAR, *TEACHING_VIEW_ROLES),
    },
    "examinations": {
        "view": ADMIN_ROLES + (REGISTRAR, EXAM_OFFICER, *TEACHING_VIEW_ROLES),
        "create": ADMIN_ROLES + EXAMINATION_MANAGE_ROLES,
        "update": ADMIN_ROLES + EXAMINATION_MANAGE_ROLES,
        "delete_or_archive": ADMIN_ROLES,
        "submit": ADMIN_ROLES + EXAMINATION_MANAGE_ROLES,
        "review": ADMIN_ROLES + (EXAM_OFFICER, HOD, PRINCIPAL, VICE_PRINCIPAL),
        "approve": ADMIN_ROLES + (EXAM_OFFICER, PRINCIPAL, VICE_PRINCIPAL),
        "publish": ADMIN_ROLES + (EXAM_OFFICER, PRINCIPAL, VICE_PRINCIPAL),
        "export": ADMIN_ROLES + (REGISTRAR, HOD, EXAM_OFFICER, PRINCIPAL),
        "print": ADMIN_ROLES + (REGISTRAR, HOD, EXAM_OFFICER, PRINCIPAL),
    },
    "transcripts": {
        "view": ADMIN_ROLES
        + (REGISTRAR, HOD, EXAM_OFFICER, PRINCIPAL, VICE_PRINCIPAL),
        "create": ADMIN_ROLES + (REGISTRAR, EXAM_OFFICER),
        "update": ADMIN_ROLES + (REGISTRAR,),
        "delete_or_archive": ADMIN_ROLES,
        "review": ADMIN_ROLES + (HOD, EXAM_OFFICER, PRINCIPAL, VICE_PRINCIPAL),
        "approve": ADMIN_ROLES + (EXAM_OFFICER, PRINCIPAL, VICE_PRINCIPAL),
        "issue_or_revoke": ADMIN_ROLES + (REGISTRAR, PRINCIPAL),
        "download": ADMIN_ROLES
        + (REGISTRAR, HOD, EXAM_OFFICER, PRINCIPAL, VICE_PRINCIPAL),
        "print": ADMIN_ROLES
        + (REGISTRAR, HOD, EXAM_OFFICER, PRINCIPAL, VICE_PRINCIPAL),
        "export": ADMIN_ROLES + (REGISTRAR, PRINCIPAL),
    },
    "alumni": {
        "view": ADMIN_ROLES
        + (REGISTRAR, HOD, EXAM_OFFICER, PRINCIPAL, VICE_PRINCIPAL),
        "export": ADMIN_ROLES + (REGISTRAR, PRINCIPAL),
    },
    "finance": {
        "view": ADMIN_ROLES
        + (REGISTRAR, HOD, PRINCIPAL, VICE_PRINCIPAL, "Bursar/Accountant"),
        "create": ADMIN_ROLES + ("Bursar/Accountant",),
        "update": ADMIN_ROLES + ("Bursar/Accountant",),
        "delete_or_archive": ADMIN_ROLES,
        "approve": ADMIN_ROLES + (PRINCIPAL, VICE_PRINCIPAL),
        "reverse_or_refund": ADMIN_ROLES + ("Bursar/Accountant",),
        "export": ADMIN_ROLES + ("Bursar/Accountant", REGISTRAR),
        "print": ADMIN_ROLES
        + (REGISTRAR, PRINCIPAL, VICE_PRINCIPAL, "Bursar/Accountant"),
    },
}
