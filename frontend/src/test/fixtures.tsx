import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import App from "../App";
import { AuthProvider, type RoleAssignment, type User } from "../auth/AuthContext";

export type FetchResponses = Record<string, unknown>;

function role(name: string): RoleAssignment {
  return {
    role: name,
    role_id: `role-${name}`,
    is_system: true,
    scope_type: "institution",
    scope_ref_id: null,
    institution_id: "inst-1",
  };
}

function makeUser(roleName: string): User {
  return {
    id: "user-1",
    email: `${roleName.toLowerCase().replace(/[^a-z]+/g, "-")}@school.test`,
    first_name: "Test",
    last_name: "User",
    institution: "inst-1",
    campus: "campus-1",
    is_staff: false,
    is_active: true,
    roles: [role(roleName)],
  };
}

export const ADMIN_USER = makeUser("Institution Administrator");
export const TEACHER_USER = makeUser("Subject Teacher");
export const EXAM_OFFICER_USER = makeUser("Examination Officer");
export const REGISTRAR_USER = makeUser("Registrar/Admissions");

export function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export function paginated<T>(results: T[]) {
  return { count: results.length, next: null, previous: null, results };
}

export const SESSION = { id: "session-1", name: "2026/2027", code: "2026", start_date: "2026-09-01", end_date: "2027-06-30", is_closed: false };
export const TERM = { id: "term-1", session: "session-1", name: "First term", code: "T1", start_date: "2026-09-01", end_date: "2026-12-18", is_closed: false };
export const CLASS_LEVEL = { id: "class-1", name: "Grade 10", code: "G10" };
export const SUBJECT = { id: "subject-1", name: "Mathematics", code: "MTH" };
export const OFFERING = { id: "offering-1", session: "session-1", term: "term-1", class_level: "class-1", subject: "subject-1" };
export const EMPLOYEE = { id: "employee-1", employee_number: "EMP-1", first_name: "Ada", last_name: "Lovelace" };
export const STUDENT = { id: "student-1", admission_number: "STU-1", first_name: "Grace", last_name: "Hopper" };
export const COMPONENT = { id: "component-1", scheme: "scheme-1", code: "CA", name: "Continuous assessment", max_marks: "40", weight: "40" };
export const SCHEME = { id: "scheme-1", name: "Grade 10 scheme", code: "G10-2026" };
export const RESULT = {
  id: "result-1",
  student: "student-1",
  offering: "offering-1",
  scheme: "scheme-1",
  total_score: "72.00",
  grade: "B",
  status: "submitted",
  component_scores: { CA: "32" },
};
export const REPORT_CARD = { id: "card-1", reference: "RC-2026-1", student: "student-1", session: "session-1", term: "term-1", version: 1, status: "published", published_at: "2026-11-01" };
export const TRANSCRIPT_REQUEST = { id: "request-1", student: "student-1", purpose: "University application", requested_kind: "official", status: "approved", decision_reason: "" };
export const TRANSCRIPT = { id: "transcript-1", reference_number: "TR-2026-1", student: "student-1", version: 1, kind: "official", status: "issued", issued_to: "Grace Hopper" };

export function baseResponses(user: User | null = ADMIN_USER): FetchResponses {
  return {
    "/auth/csrf/": { csrfToken: "test-token" },
    "/auth/me/": user ? { user } : jsonResponse({ detail: "Not authenticated" }, 401),
    "/auth/login/": { user: user || ADMIN_USER },
    "/auth/logout/": {},
    "/health/": { status: "ok", database: "ready" },
    "/academic-sessions/": paginated([SESSION]),
    "/terms/": paginated([TERM]),
    "/class-levels/": paginated([CLASS_LEVEL]),
    "/subjects/": paginated([SUBJECT]),
    "/subject-offerings/": paginated([OFFERING]),
    "/employees/": paginated([EMPLOYEE]),
    "/students/": paginated([STUDENT]),
    "/teacher-assignments/": paginated([{ id: "assignment-1", employee: "employee-1", offering: "offering-1", role: "lead", start_date: "2026-09-01", end_date: "2027-06-30", workload_hours: 12, status: "active" }]),
    "/teacher-assignments/my-assignments/": [{ id: "assignment-1", employee: "employee-1", offering: "offering-1", role: "lead", start_date: "2026-09-01", end_date: "2027-06-30", workload_hours: 12, status: "active" }],
    "/workload-policies/": paginated([{ id: "policy-1", name: "Standard", max_hours: 40, effective_from: "2026-09-01", effective_to: null }]),
    "/timetables/": paginated([{ id: "timetable-1", name: "Grade 10 timetable", session: "session-1", class_level: "class-1", version: 1, status: "draft" }]),
    "/timetable-slots/": paginated([{ id: "slot-1", timetable: "timetable-1", day_of_week: 1, period: 1, offering: "offering-1", employee: "employee-1", room: "R1", recurrence: "weekly", recurrence_interval: 1, recurrence_until: null }]),
    "/attendance-sessions/": paginated([{ id: "attendance-1", attendance_date: "2026-11-20", offering: "offering-1", status: "open" }]),
    "/attendance-records/": paginated([{ id: "record-1", attendance_session: "attendance-1", student: "student-1", status: "present", correction_count: 0 }]),
    "/attendance-sessions/attendance-1/expected-students/": [{ id: "student-1", admission_number: "STU-1", name: "Grace Hopper" }],
    "/teacher-attendance/query/": [{ id: "teacher-record-1", employee: "employee-1", attendance_date: "2026-11-20", status: "present", approval_status: "draft" }],
    "/examinations/results/": paginated([RESULT]),
    "/examinations/assessment-schemes/": paginated([SCHEME]),
    "/examinations/assessment-components/": paginated([COMPONENT]),
    "/examinations/report-cards/": paginated([REPORT_CARD]),
    "/transcripts/requests/": paginated([TRANSCRIPT_REQUEST]),
    "/transcripts/": paginated([TRANSCRIPT]),
  };
}

function apiPath(url: URL): string {
  const configured = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";
  const base = new URL(configured, url.origin).pathname.replace(/\/$/, "");
  let pathname = url.pathname;
  if (base && pathname.startsWith(`${base}/`)) pathname = pathname.slice(base.length);
  return `${pathname}${url.search}`;
}

export function installFetch(responses: FetchResponses) {
  const mock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const url = new URL(String(input), "http://localhost");
    const path = apiPath(url);
    const pathname = url.pathname.replace(/^\/api\/v1/, "");
    const method = (init?.method || "GET").toUpperCase();
    const handler = responses[`${method} ${path}`] ?? responses[path] ?? responses[pathname] ?? responses[`${method} ${pathname}`];
    const value = typeof handler === "function" ? await (handler as (options?: RequestInit) => unknown)(init) : handler;
    if (value instanceof Response) return value;
    if (value === undefined) return new Response(null, { status: 404 });
    if (value === null) return new Response(null, { status: 204 });
    return jsonResponse(value);
  });
  vi.stubGlobal("fetch", mock);
  return mock;
}

export function renderApp({ route = "/", user = ADMIN_USER, responses = {} }: { route?: string; user?: User | null; responses?: FetchResponses } = {}) {
  const fetchMock = installFetch({ ...baseResponses(user), ...responses });
  const view = render(
    <MemoryRouter initialEntries={[route]}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </MemoryRouter>,
  );
  return { ...view, fetchMock };
}
