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
    "employees": {
        "view": ADMIN_ROLES + ("Registrar/Admissions", "Academic Head"),
        "create": ADMIN_ROLES + ("Registrar/Admissions",),
        "update": ADMIN_ROLES + ("Registrar/Admissions",),
        "delete_or_archive": ADMIN_ROLES,
        "export": ADMIN_ROLES,
    },
    "academics": {
        "view": ADMIN_ROLES + ("Registrar/Admissions", "Academic Head", "Teacher"),
        "create": ADMIN_ROLES + ("Registrar/Admissions", "Academic Head"),
        "update": ADMIN_ROLES + ("Registrar/Admissions", "Academic Head"),
        "delete_or_archive": ADMIN_ROLES,
        "publish": ADMIN_ROLES + ("Academic Head",),
        "export": ADMIN_ROLES,
    },
    "teaching": {
        "view": ADMIN_ROLES + ("Registrar/Admissions", "Academic Head", "Teacher"),
        "create": ADMIN_ROLES + ("Registrar/Admissions", "Academic Head"),
        "update": ADMIN_ROLES + ("Academic Head",),
        "delete_or_archive": ADMIN_ROLES,
        "publish": ADMIN_ROLES + ("Academic Head",),
        "approve": ADMIN_ROLES + ("Academic Head",),
        "export": ADMIN_ROLES,
    },
    "attendance": {
        "view": ADMIN_ROLES + ("Registrar/Admissions", "Academic Head", "Teacher"),
        "create": ADMIN_ROLES + ("Registrar/Admissions", "Academic Head", "Teacher"),
        "update": ADMIN_ROLES + ("Registrar/Admissions", "Academic Head"),
        "delete_or_archive": ADMIN_ROLES,
        "approve": ADMIN_ROLES + ("Academic Head",),
        "export": ADMIN_ROLES,
        "print": ADMIN_ROLES + ("Registrar/Admissions", "Academic Head", "Teacher"),
    },
    "examinations": {
        "view": ADMIN_ROLES
        + (
            "Registrar/Admissions",
            "Academic Head",
            "Teacher",
            "Examination Officer",
            "Principal/VP",
        ),
        "create": ADMIN_ROLES + ("Academic Head", "Teacher", "Examination Officer"),
        "update": ADMIN_ROLES + ("Academic Head", "Teacher", "Examination Officer"),
        "delete_or_archive": ADMIN_ROLES,
        "submit": ADMIN_ROLES + ("Academic Head", "Teacher", "Examination Officer"),
        "review": ADMIN_ROLES + ("Academic Head", "Examination Officer", "Principal/VP"),
        "approve": ADMIN_ROLES + ("Examination Officer", "Principal/VP"),
        "publish": ADMIN_ROLES + ("Examination Officer", "Principal/VP"),
        "export": ADMIN_ROLES + ("Registrar/Admissions", "Academic Head", "Examination Officer"),
        "print": ADMIN_ROLES + ("Registrar/Admissions", "Academic Head", "Examination Officer"),
    },
    "transcripts": {
        "view": ADMIN_ROLES
        + ("Registrar/Admissions", "Academic Head", "Examination Officer", "Principal/VP"),
        "create": ADMIN_ROLES + ("Registrar/Admissions", "Examination Officer"),
        "update": ADMIN_ROLES + ("Registrar/Admissions",),
        "delete_or_archive": ADMIN_ROLES,
        "review": ADMIN_ROLES + ("Academic Head", "Examination Officer", "Principal/VP"),
        "approve": ADMIN_ROLES + ("Examination Officer", "Principal/VP"),
        "issue_or_revoke": ADMIN_ROLES + ("Registrar/Admissions", "Principal/VP"),
        "download": ADMIN_ROLES
        + ("Registrar/Admissions", "Academic Head", "Examination Officer", "Principal/VP"),
        "print": ADMIN_ROLES
        + ("Registrar/Admissions", "Academic Head", "Examination Officer", "Principal/VP"),
        "export": ADMIN_ROLES + ("Registrar/Admissions", "Principal/VP"),
    },
}
