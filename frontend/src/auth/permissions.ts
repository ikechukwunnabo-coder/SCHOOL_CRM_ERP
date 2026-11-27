import type { User } from "../auth/AuthContext";

export type ModuleKey =
  | "academics"
  | "teaching"
  | "attendance"
  | "examinations"
  | "transcripts"
  | "finance"
  | "accounting"
  | "notifications";
export type VerbKey =
  | "view"
  | "create"
  | "update"
  | "approve"
  | "publish"
  | "review"
  | "print"
  | "issue_or_revoke"
  | "download"
  | "export";

const ADMIN = ["Super Administrator", "Institution Administrator", "Campus Administrator"];
const REGISTRAR = "Registrar/Admissions";
const EXAM_OFFICER = "Examination Officer";
const HOD = "Head of Department";
const PRINCIPAL = "Principal/Head Teacher";
const VICE_PRINCIPAL = "Vice Principal/Deputy Head";
const CLASS_TEACHER = "Class Teacher";
const SUBJECT_TEACHER = "Subject Teacher";
const HR_OFFICER = "HR Officer";
const BURSAR = "Bursar/Accountant";
const TEACHING_VIEW = [HOD, CLASS_TEACHER, SUBJECT_TEACHER, PRINCIPAL, VICE_PRINCIPAL];

const ROLE_ALIASES: Record<string, string[]> = {
  "Academic Head": [HOD],
  Principal: [PRINCIPAL],
  "Principal/VP": [PRINCIPAL, VICE_PRINCIPAL],
  Teacher: [SUBJECT_TEACHER],
};

const GRANTS: Record<ModuleKey, Partial<Record<VerbKey, string[]>>> = {
  academics: {
    view: [...ADMIN, REGISTRAR, ...TEACHING_VIEW],
    create: [...ADMIN, REGISTRAR, HOD, PRINCIPAL],
    update: [...ADMIN, REGISTRAR, HOD, PRINCIPAL],
    publish: [...ADMIN, HOD, PRINCIPAL],
  },
  teaching: {
    view: [...ADMIN, REGISTRAR, ...TEACHING_VIEW],
    create: [...ADMIN, REGISTRAR, HOD, PRINCIPAL],
    update: [...ADMIN, HOD, PRINCIPAL],
    approve: [...ADMIN, HOD, PRINCIPAL, VICE_PRINCIPAL],
    publish: [...ADMIN, HOD, PRINCIPAL],
  },
  attendance: {
    view: [...ADMIN, REGISTRAR, ...TEACHING_VIEW],
    create: [...ADMIN, REGISTRAR, HOD, CLASS_TEACHER, SUBJECT_TEACHER],
    update: [...ADMIN, HOD, CLASS_TEACHER, SUBJECT_TEACHER],
    approve: [...ADMIN, HOD, PRINCIPAL],
  },
  examinations: {
    view: [...ADMIN, REGISTRAR, EXAM_OFFICER, ...TEACHING_VIEW],
    create: [...ADMIN, HOD, SUBJECT_TEACHER, EXAM_OFFICER, PRINCIPAL],
    update: [...ADMIN, HOD, SUBJECT_TEACHER, EXAM_OFFICER, PRINCIPAL],
    review: [...ADMIN, EXAM_OFFICER, HOD, PRINCIPAL, VICE_PRINCIPAL],
    approve: [...ADMIN, EXAM_OFFICER, PRINCIPAL, VICE_PRINCIPAL],
    publish: [...ADMIN, EXAM_OFFICER, PRINCIPAL, VICE_PRINCIPAL],
    print: [...ADMIN, REGISTRAR, HOD, EXAM_OFFICER, PRINCIPAL],
  },
  transcripts: {
    view: [...ADMIN, REGISTRAR, HOD, EXAM_OFFICER, PRINCIPAL, VICE_PRINCIPAL],
    create: [...ADMIN, REGISTRAR, EXAM_OFFICER],
    update: [...ADMIN, REGISTRAR],
    review: [...ADMIN, HOD, EXAM_OFFICER, PRINCIPAL, VICE_PRINCIPAL],
    approve: [...ADMIN, EXAM_OFFICER, PRINCIPAL, VICE_PRINCIPAL],
    issue_or_revoke: [...ADMIN, REGISTRAR, PRINCIPAL],
    print: [...ADMIN, REGISTRAR, HOD, EXAM_OFFICER, PRINCIPAL, VICE_PRINCIPAL],
    download: [...ADMIN, REGISTRAR, HOD, EXAM_OFFICER, PRINCIPAL, VICE_PRINCIPAL],
  },
  finance: {
    view: [...ADMIN, REGISTRAR, BURSAR, PRINCIPAL, VICE_PRINCIPAL, "Parent/Guardian"],
    create: [...ADMIN, BURSAR],
    update: [...ADMIN, BURSAR],
    approve: [...ADMIN, BURSAR, PRINCIPAL],
    export: [...ADMIN, BURSAR, PRINCIPAL],
  },
  accounting: {
    view: [...ADMIN, BURSAR, PRINCIPAL, VICE_PRINCIPAL],
    create: [...ADMIN, BURSAR],
    update: [...ADMIN, BURSAR],
    approve: [...ADMIN, BURSAR, PRINCIPAL],
    export: [...ADMIN, BURSAR, PRINCIPAL],
  },
  notifications: {
    view: [...ADMIN, REGISTRAR, BURSAR, PRINCIPAL, VICE_PRINCIPAL],
    create: [...ADMIN, REGISTRAR, BURSAR],
    update: [...ADMIN, REGISTRAR, BURSAR],
    export: [...ADMIN, REGISTRAR, BURSAR, PRINCIPAL],
  },
};

export function roleNames(user: User | null): string[] {
  if (!user) return [];
  const names = new Set<string>();
  for (const assignment of user.roles || []) {
    const role = assignment.role;
    names.add(role);
    for (const alias of ROLE_ALIASES[role] || []) names.add(alias);
  }
  return [...names];
}

export function can(user: User | null, module: ModuleKey, verb: VerbKey): boolean {
  if (!user) return false;
  const allowed = GRANTS[module][verb] || [];
  const held = new Set(roleNames(user));
  return allowed.some((role) => held.has(role));
}

export function hasAnyRole(user: User | null, roles: string[]): boolean {
  const held = new Set(roleNames(user));
  return roles.some((role) => held.has(role));
}

export { ADMIN, BURSAR, CLASS_TEACHER, EXAM_OFFICER, HOD, HR_OFFICER, PRINCIPAL, REGISTRAR, SUBJECT_TEACHER, VICE_PRINCIPAL };
