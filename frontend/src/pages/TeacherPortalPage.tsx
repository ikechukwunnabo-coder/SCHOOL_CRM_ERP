import { useEffect, useState } from "react";
import { apiFetch } from "../api/client";
import { ErrorBanner, LoadingState, PageHeading } from "../components/Feedback";
import { Panel } from "../components/Panel";

export function TeacherPortalPage() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    apiFetch<Record<string, unknown>>("/portal/").then(setData).catch((e: Error) => setError(e.message));
  }, []);
  return (
    <div className="page-stack">
      <PageHeading title="Teacher portal" description="Assignments, timetable, and attendance summary for the signed-in teacher." />
      {error ? <ErrorBanner message={error} /> : null}
      {!data && !error ? <LoadingState /> : null}
      {data ? (
        <>
          <Panel title="Overview">
            <pre className="small">{JSON.stringify(data.teacher, null, 2)}</pre>
          </Panel>
          <Panel title="Assignments">
            <pre className="small">{JSON.stringify(data.assignments, null, 2)}</pre>
          </Panel>
          <Panel title="Timetable slots">
            <pre className="small">{JSON.stringify(data.timetable_slots, null, 2)}</pre>
          </Panel>
          <Panel title="Attendance">
            <pre className="small">{JSON.stringify({ sessions: data.attendance_sessions, teacher: data.teacher_attendance }, null, 2)}</pre>
          </Panel>
        </>
      ) : null}
    </div>
  );
}
