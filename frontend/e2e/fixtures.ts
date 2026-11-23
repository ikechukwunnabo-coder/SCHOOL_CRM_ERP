import { expect, type Page, type Request as PlaywrightRequest, type Route } from "@playwright/test";

type Row = { id: string } & Record<string, unknown>;
type Call = { method: string; path: string; body: Record<string, unknown> };

export type ApiState = {
  signedIn: boolean;
  calls: Call[];
  sessions: Row[];
  terms: Row[];
  timetables: Row[];
  attendanceSessions: Row[];
  attendanceRecords: Row[];
  teacherAttendance: Row[];
  results: Row[];
  reportCards: Row[];
  transcriptRequests: Row[];
  transcripts: Row[];
};

const USER = {
  id: "user-1",
  email: "admin@school.test",
  first_name: "Test",
  last_name: "Administrator",
  institution: "inst-1",
  campus: "campus-1",
  is_staff: false,
  is_active: true,
  roles: [
    {
      role: "Institution Administrator",
      role_id: "role-admin",
      is_system: true,
      scope_type: "institution",
      scope_ref_id: null,
      institution_id: "inst-1",
    },
  ],
};

export function paginated<T>(results: T[]) {
  return { count: results.length, next: null, previous: null, results };
}

function requestBody(request: PlaywrightRequest): Record<string, unknown> {
  const raw = request.postData();
  if (!raw) return {};
  try {
    return JSON.parse(raw) as Record<string, unknown>;
  } catch {
    return {};
  }
}

async function json(route: Route, data: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(data) });
}

function updateRow(rows: Row[], id: string, changes: Record<string, unknown>) {
  const row = rows.find((item) => item.id === id);
  if (row) Object.assign(row, changes);
}

export async function mockApi(page: Page): Promise<ApiState> {
  const state: ApiState = {
    signedIn: false,
    calls: [],
    sessions: [{ id: "session-1", name: "2026/2027", code: "2026", start_date: "2026-09-01", end_date: "2027-06-30", is_closed: false }],
    terms: [{ id: "term-1", session: "session-1", name: "First term", code: "T1", start_date: "2026-09-01", end_date: "2026-12-18", is_closed: false }],
    timetables: [{ id: "timetable-1", name: "Grade 10 timetable", session: "session-1", class_level: "class-1", version: 1, status: "draft" }],
    attendanceSessions: [{ id: "attendance-1", attendance_date: "2026-11-20", offering: "offering-1", status: "open" }],
    attendanceRecords: [{ id: "record-1", attendance_session: "attendance-1", student: "student-1", status: "present", correction_count: 0 }],
    teacherAttendance: [{ id: "teacher-record-1", employee: "employee-1", attendance_date: "2026-11-20", status: "present", approval_status: "draft" }],
    results: [{
      id: "result-1",
      student: "student-1",
      offering: "offering-1",
      scheme: "scheme-1",
      total_score: "72.00",
      grade: "B",
      status: "submitted",
      component_scores: { CA: "32" },
    }],
    reportCards: [{ id: "card-1", reference: "RC-2026-1", student: "student-1", session: "session-1", term: "term-1", version: 1, status: "published", published_at: "2026-11-01" }],
    transcriptRequests: [{ id: "request-1", student: "student-1", purpose: "University application", requested_kind: "official", status: "approved", decision_reason: "" }],
    transcripts: [{ id: "transcript-1", reference_number: "TR-2026-1", student: "student-1", version: 1, kind: "official", status: "generated", issued_to: "" }],
  };

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace(/^\/api\/v1/, "") || "/";
    const method = request.method();
    const body = requestBody(request);
    state.calls.push({ method, path, body });

    if (method === "GET" && path === "/auth/csrf/") return json(route, { csrfToken: "e2e-token" });
    if (method === "GET" && path === "/auth/me/") {
      return state.signedIn ? json(route, { user: USER }) : json(route, { detail: "Not authenticated" }, 401);
    }
    if (method === "POST" && path === "/auth/login/") {
      state.signedIn = true;
      return json(route, { user: USER });
    }
    if (method === "POST" && path === "/auth/logout/") {
      state.signedIn = false;
      return json(route, {});
    }
    if (method === "GET" && path === "/health/") return json(route, { status: "ok", database: "ready" });

    if (method === "GET" && /^\/attendance-sessions\/[^/]+\/expected-students\/$/.test(path)) {
      return json(route, [{ id: "student-1", admission_number: "STU-1", name: "Grace Hopper" }]);
    }
    if (method === "GET" && /^\/examinations\/report-cards\/[^/]+\/download\/$/.test(path)) {
      await route.fulfill({
        status: 200,
        contentType: "application/pdf",
        headers: { "content-disposition": 'attachment; filename="RC-2026-1.pdf"' },
        body: "%PDF-1.4 report card",
      });
      return;
    }
    if (method === "GET" && /^\/transcripts\/[^/]+\/download\/$/.test(path)) {
      await route.fulfill({
        status: 200,
        contentType: "application/pdf",
        headers: { "content-disposition": 'attachment; filename="TR-2026-1.pdf"' },
        body: "%PDF-1.4 transcript",
      });
      return;
    }

    const lists: Record<string, Row[]> = {
      "/academic-sessions/": state.sessions,
      "/terms/": state.terms,
      "/class-levels/": [{ id: "class-1", name: "Grade 10", code: "G10" }],
      "/subjects/": [{ id: "subject-1", name: "Mathematics", code: "MTH" }],
      "/subject-offerings/": [{ id: "offering-1", session: "session-1", term: "term-1", class_level: "class-1", subject: "subject-1" }],
      "/employees/": [{ id: "employee-1", employee_number: "EMP-1", first_name: "Ada", last_name: "Lovelace" }],
      "/students/": [{ id: "student-1", admission_number: "STU-1", first_name: "Grace", last_name: "Hopper" }],
      "/teacher-assignments/": [{ id: "assignment-1", employee: "employee-1", offering: "offering-1", role: "lead", start_date: "2026-09-01", end_date: "2027-06-30", workload_hours: 12, status: "active" }],
      "/teacher-assignments/my-assignments/": [{ id: "assignment-1", employee: "employee-1", offering: "offering-1", role: "lead", start_date: "2026-09-01", end_date: "2027-06-30", workload_hours: 12, status: "active" }],
      "/workload-policies/": [{ id: "policy-1", name: "Standard", max_hours: 40, effective_from: "2026-09-01", effective_to: null }],
      "/timetables/": state.timetables,
      "/timetable-slots/": [{ id: "slot-1", timetable: "timetable-1", day_of_week: 1, period: 1, offering: "offering-1", employee: "employee-1", room: "R1", recurrence: "weekly", recurrence_interval: 1, recurrence_until: null }],
      "/attendance-sessions/": state.attendanceSessions,
      "/attendance-records/": state.attendanceRecords,
      "/teacher-attendance/query/": state.teacherAttendance,
      "/examinations/results/": state.results,
      "/examinations/assessment-schemes/": [{ id: "scheme-1", name: "Grade 10 scheme", code: "G10-2026" }],
      "/examinations/assessment-components/": [{ id: "component-1", scheme: "scheme-1", code: "CA", name: "Continuous assessment", max_marks: "40", weight: "40" }],
      "/examinations/report-cards/": state.reportCards,
      "/transcripts/requests/": state.transcriptRequests,
      "/transcripts/": state.transcripts,
    };
    if (method === "GET" && lists[path]) return json(route, paginated(lists[path]));

    if (method === "POST" && path === "/academic-sessions/") {
      const row: Row = { id: `session-${state.sessions.length + 1}`, ...body, is_closed: false };
      state.sessions.push(row);
      return json(route, row, 201);
    }
    if (method === "POST" && path === "/terms/") {
      const row: Row = { id: `term-${state.terms.length + 1}`, ...body, is_closed: false };
      state.terms.push(row);
      return json(route, row, 201);
    }
    if (method === "POST" && path === "/timetables/") {
      const row: Row = { id: `timetable-${state.timetables.length + 1}`, ...body, version: 1, status: "draft" };
      state.timetables.push(row);
      return json(route, row, 201);
    }
    if (method === "POST" && path === "/attendance-sessions/open/") {
      const row: Row = { id: `attendance-${state.attendanceSessions.length + 1}`, ...body, status: "open" };
      state.attendanceSessions.push(row);
      return json(route, row, 201);
    }
    if (method === "POST" && path === "/workload-policies/") {
      return json(route, { id: `policy-${state.calls.length}`, ...body }, 201);
    }
    if (method === "POST" && path === "/teacher-attendance/mark/") {
      const row: Row = { id: `teacher-record-${state.teacherAttendance.length + 1}`, ...body, approval_status: "draft" };
      state.teacherAttendance.push(row);
      return json(route, row, 201);
    }
    if (method === "POST" && path === "/examinations/results/") {
      const row: Row = { id: `result-${state.results.length + 1}`, ...body, total_score: "0.00", grade: "-", status: "draft" };
      state.results.push(row);
      return json(route, row, 201);
    }
    if (method === "POST" && path === "/examinations/results/submit/") return json(route, { submitted: 1 });
    if (method === "POST" && path === "/examinations/report-cards/generate/") {
      const row: Row = {
        id: `card-${state.reportCards.length + 1}`,
        reference: `RC-2026-${state.reportCards.length + 1}`,
        student: String(body.student),
        session: String(body.session),
        term: body.term || null,
        version: 1,
        status: "published",
        published_at: "2026-11-23",
      };
      state.reportCards.push(row);
      return json(route, row, 201);
    }
    if (method === "POST" && path === "/transcripts/requests/") {
      const row: Row = { id: `request-${state.transcriptRequests.length + 1}`, ...body, status: "submitted", decision_reason: "" };
      state.transcriptRequests.push(row);
      return json(route, row, 201);
    }
    if (method === "POST" && path === "/transcripts/verify/") {
      return json(route, {
        valid: true,
        status: "valid",
        checked_at: "2026-11-23T12:00:00Z",
        institution: { name: "Example School", code: "EX" },
        reference_number: "TR-2026-1",
        version: 1,
        kind: "official",
      });
    }

    let match = path.match(/^\/academic-sessions\/([^/]+)\/close\/$/);
    if (method === "POST" && match) {
      updateRow(state.sessions, match[1], { is_closed: true });
      return json(route, { id: match[1], is_closed: true });
    }
    match = path.match(/^\/timetables\/([^/]+)\/(add-slot|approve|publish|revise)\/$/);
    if (method === "POST" && match) {
      const [, id, action] = match;
      const changes = action === "approve" ? { approved_at: "2026-11-23T12:00:00Z" } : action === "publish" ? { status: "published" } : action === "revise" ? { status: "draft", version: 2 } : {};
      updateRow(state.timetables, id, changes);
      return json(route, { id, action, ...changes });
    }
    match = path.match(/^\/teacher-assignments\/([^/]+)\/reassign\/$/);
    if (method === "POST" && match) return json(route, { id: match[1], ...body });
    match = path.match(/^\/attendance-sessions\/([^/]+)\/mark\/$/);
    if (method === "POST" && match) {
      const row: Row = { id: `record-${state.attendanceRecords.length + 1}`, attendance_session: match[1], ...body, correction_count: 0 };
      state.attendanceRecords.push(row);
      return json(route, row, 201);
    }
    match = path.match(/^\/attendance-sessions\/([^/]+)\/close\/$/);
    if (method === "POST" && match) {
      updateRow(state.attendanceSessions, match[1], { status: "closed" });
      return json(route, { id: match[1], status: "closed" });
    }
    match = path.match(/^\/attendance-records\/([^/]+)\/correct\/$/);
    if (method === "POST" && match) {
      updateRow(state.attendanceRecords, match[1], { status: body.new_status, correction_count: 1 });
      return json(route, { id: match[1], ...body });
    }
    match = path.match(/^\/teacher-attendance\/([^/]+)\/approve\/$/);
    if (method === "POST" && match) {
      updateRow(state.teacherAttendance, match[1], { approval_status: "approved" });
      return json(route, { id: match[1], approval_status: "approved" });
    }
    match = path.match(/^\/examinations\/results\/([^/]+)\/(approve|publish|return-for-correction|correct)\/$/);
    if (method === "POST" && match) {
      const [, id, action] = match;
      const status = action === "approve" ? "approved" : action === "publish" ? "published" : "submitted";
      updateRow(state.results, id, { status, ...(action === "correct" ? { component_scores: body.component_scores } : {}) });
      return json(route, { id, status });
    }
    match = path.match(/^\/transcripts\/requests\/([^/]+)\/(review|approve|reject|generate)\/$/);
    if (method === "POST" && match) {
      const [, id, action] = match;
      const status = action === "generate" ? "generated" : `${action}ed`;
      updateRow(state.transcriptRequests, id, { status, decision_reason: String(body.reason || "") });
      return json(route, { id, verification_token: action === "generate" ? "verify-token-123" : undefined });
    }
    match = path.match(/^\/transcripts\/([^/]+)\/(issue|correct|revoke)\/$/);
    if (method === "POST" && match) {
      const [, id, action] = match;
      const status = action === "issue" ? "issued" : action === "correct" ? "corrected" : "revoked";
      updateRow(state.transcripts, id, { status, ...(action === "issue" ? { issued_to: String(body.issued_to || "") } : {}) });
      return json(route, { id, verification_token: action === "correct" ? "verify-token-123" : undefined });
    }

    return json(route, { detail: `Unhandled ${method} ${path}` }, 404);
  });
  return state;
}

export function panel(page: Page, title: string) {
  return page.locator("section").filter({ has: page.getByRole("heading", { name: title, exact: true }) });
}

export async function goToWorkflow(page: Page, label: string) {
  await page.getByRole("navigation", { name: "Main navigation" }).getByRole("link", { name: label, exact: true }).click();
}

export async function login(page: Page): Promise<ApiState> {
  const state = await mockApi(page);
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "School CRM & ERP", level: 1 })).toBeVisible();
  await page.getByLabel("Email").fill("admin@school.test");
  await page.getByLabel("Password").fill("Passw0rd!");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "School operations", level: 2 })).toBeVisible();
  return state;
}
