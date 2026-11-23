SUPER_ADMIN = "Super Administrator"
INSTITUTION_ADMIN = "Institution Administrator"
CAMPUS_ADMIN = "Campus Administrator"
PRINCIPAL = "Principal/Head Teacher"
VICE_PRINCIPAL = "Vice Principal/Deputy Head"
HOD = "Head of Department"
CLASS_TEACHER = "Class Teacher"
SUBJECT_TEACHER = "Subject Teacher"
REGISTRAR = "Registrar/Admissions"
EXAM_OFFICER = "Examination Officer"
HR_OFFICER = "HR Officer"

ADMIN_ROLES = (SUPER_ADMIN, INSTITUTION_ADMIN, CAMPUS_ADMIN)
LEADERSHIP_ROLES = (PRINCIPAL, VICE_PRINCIPAL, HOD)
TEACHING_ROLES = (CLASS_TEACHER, SUBJECT_TEACHER)
CANONICAL_ROLES = (
    *ADMIN_ROLES,
    *LEADERSHIP_ROLES,
    *TEACHING_ROLES,
    REGISTRAR,
    EXAM_OFFICER,
    HR_OFFICER,
)

ROLE_ALIASES = {
    "Academic Head": (HOD,),
    "Principal": (PRINCIPAL,),
    "Principal/VP": (PRINCIPAL, VICE_PRINCIPAL),
    "Teacher": (SUBJECT_TEACHER,),
    CLASS_TEACHER: (CLASS_TEACHER,),
    SUBJECT_TEACHER: (SUBJECT_TEACHER,),
    HOD: (HOD,),
    PRINCIPAL: (PRINCIPAL,),
    VICE_PRINCIPAL: (VICE_PRINCIPAL,),
}

LEGACY_ROLE_MIGRATIONS = {
    "Academic Head": (HOD,),
    "Principal": (PRINCIPAL,),
    "Principal/VP": (PRINCIPAL, VICE_PRINCIPAL),
    "Teacher": (SUBJECT_TEACHER,),
}


def normalize_role_names(names) -> set[str]:
    normalized: set[str] = set()
    for name in names or ():
        if not name:
            continue
        aliases = ROLE_ALIASES.get(name)
        if aliases:
            normalized.update(aliases)
        else:
            normalized.add(name)
    return normalized


def role_matches(held_names, expected_names) -> bool:
    return bool(normalize_role_names(held_names) & normalize_role_names(expected_names))
