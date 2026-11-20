from apps.admissions.permissions import (
    ADMISSION_DECIDE_ROLES,
    ADMISSION_MANAGE_ROLES,
    ADMISSION_VIEW_ROLES,
)
from apps.students.permissions import STUDENT_MANAGE_ROLES, STUDENT_VIEW_ROLES

ADMIN_ROLES = (
    "Super Administrator",
    "Institution Administrator",
)

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
        "create": ("Super Administrator", "Institution Administrator", "Registrar/Admissions"),
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
        "view": ADMIN_ROLES + ("Registrar/Admissions",),
        "create": ADMIN_ROLES + ("Registrar/Admissions",),
        "approve": ADMIN_ROLES,
        "import": ADMIN_ROLES + ("Registrar/Admissions",),
        "export": ADMIN_ROLES,
    },
}
