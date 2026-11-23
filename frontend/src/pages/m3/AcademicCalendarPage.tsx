import { useAuth } from "../../auth/AuthContext";
import { can } from "../../auth/permissions";
import { apiPost, optionLabel, shortDate, text, type Entity } from "../../api/resources";
import { DataTable } from "../../components/DataTable";
import { ErrorBanner, LoadingState, Notice, PageHeading, StatusBadge } from "../../components/Feedback";
import { SelectField, TextField } from "../../components/FormControls";
import { Panel } from "../../components/Panel";
import { useAction } from "../../hooks/useAction";
import { useApiList } from "../../hooks/useApiResource";
import { useForm } from "../../hooks/useForm";

export function AcademicCalendarPage() {
  const { user } = useAuth();
  const sessions = useApiList<Entity>("/academic-sessions/");
  const terms = useApiList<Entity>("/terms/");
  const action = useAction();
  const canCreate = can(user, "academics", "create");
  const canUpdate = can(user, "academics", "update");
  const sessionForm = useForm({ name: "", code: "", startDate: "", endDate: "", institution: user?.institution || "" });
  const termForm = useForm({ session: "", name: "", code: "", startDate: "", endDate: "" });

  const sessionOptions = sessions.data.map((session) => ({ value: session.id, label: optionLabel(session) }));
  const sessionName = (id: unknown) => {
    const match = sessions.data.find((session) => session.id === id);
    return match ? text(match.name, text(match.code, text(id))) : text(id);
  };

  const createSession = (event: React.FormEvent) => {
    event.preventDefault();
    const values = sessionForm.values;
    void action.run(
      () =>
        apiPost<Entity>("/academic-sessions/", {
          name: values.name,
          code: values.code,
          start_date: values.startDate,
          end_date: values.endDate,
          institution: values.institution || user?.institution,
        }),
      () => {
        sessionForm.reset();
        sessions.reload();
        return "Academic session created.";
      },
    );
  };

  const createTerm = (event: React.FormEvent) => {
    event.preventDefault();
    const values = termForm.values;
    void action.run(
      () =>
        apiPost<Entity>("/terms/", {
          session: values.session,
          name: values.name,
          code: values.code,
          start_date: values.startDate,
          end_date: values.endDate,
        }),
      () => {
        termForm.reset();
        terms.reload();
        return "Term created.";
      },
    );
  };

  const closeSession = (id: string) => {
    void action.run(
      () => apiPost<Entity>(`/academic-sessions/${id}/close/`),
      () => {
        sessions.reload();
        return "Academic session closed.";
      },
    );
  };

  return (
    <div className="page-stack">
      <PageHeading title="Academic calendar" description="Manage sessions and terms used across academics, attendance, and examinations." />
      <ErrorBanner message={action.error || sessions.error || terms.error} />
      <Notice message={action.notice} />

      {canCreate ? (
        <div className="grid">
          <Panel title="New academic session" description="Dates define the active planning window.">
            <form className="form" onSubmit={createSession}>
              {user?.institution ? null : <TextField label="Institution ID" value={sessionForm.values.institution} onChange={(value) => sessionForm.setField("institution", value)} required />}
              <TextField label="Name" value={sessionForm.values.name} onChange={(value) => sessionForm.setField("name", value)} required />
              <TextField label="Code" value={sessionForm.values.code} onChange={(value) => sessionForm.setField("code", value)} required />
              <TextField label="Start date" type="date" value={sessionForm.values.startDate} onChange={(value) => sessionForm.setField("startDate", value)} required />
              <TextField label="End date" type="date" value={sessionForm.values.endDate} onChange={(value) => sessionForm.setField("endDate", value)} required />
              <button type="submit" disabled={action.busy}>Create session</button>
            </form>
          </Panel>
          <Panel title="New term" description="Terms belong to an academic session.">
            <form className="form" onSubmit={createTerm}>
              <SelectField label="Academic session" value={termForm.values.session} onChange={(value) => termForm.setField("session", value)} options={sessionOptions} required />
              <TextField label="Name" value={termForm.values.name} onChange={(value) => termForm.setField("name", value)} required />
              <TextField label="Code" value={termForm.values.code} onChange={(value) => termForm.setField("code", value)} required />
              <TextField label="Start date" type="date" value={termForm.values.startDate} onChange={(value) => termForm.setField("startDate", value)} required />
              <TextField label="End date" type="date" value={termForm.values.endDate} onChange={(value) => termForm.setField("endDate", value)} required />
              <button type="submit" disabled={action.busy || !sessionOptions.length}>Create term</button>
            </form>
          </Panel>
        </div>
      ) : (
        <Panel title="Read-only access" description="Your role can view the calendar but cannot change sessions or terms." />
      )}

      <Panel title="Academic sessions">
        {sessions.loading ? <LoadingState /> : null}
        <DataTable
          rows={sessions.data}
          columns={[
            { key: "name", label: "Session", render: (row) => text(row.name) },
            { key: "code", label: "Code", render: (row) => text(row.code) },
            { key: "dates", label: "Dates", render: (row) => `${shortDate(row.start_date)} to ${shortDate(row.end_date)}` },
            { key: "status", label: "Status", render: (row) => <StatusBadge value={row.is_closed ? "closed" : "open"} /> },
            {
              key: "actions",
              label: "Actions",
              render: (row) =>
                canUpdate && !row.is_closed ? (
                  <button type="button" className="small-button" disabled={action.busy} onClick={() => closeSession(row.id)}>
                    Close session
                  </button>
                ) : (
                  <span className="muted">-</span>
                ),
            },
          ]}
        />
      </Panel>

      <Panel title="Terms">
        {terms.loading ? <LoadingState /> : null}
        <DataTable
          rows={terms.data}
          columns={[
            { key: "name", label: "Term", render: (row) => text(row.name) },
            { key: "session", label: "Session", render: (row) => sessionName(row.session) },
            { key: "code", label: "Code", render: (row) => text(row.code) },
            { key: "dates", label: "Dates", render: (row) => `${shortDate(row.start_date)} to ${shortDate(row.end_date)}` },
            { key: "status", label: "Status", render: (row) => <StatusBadge value={row.is_closed ? "closed" : "open"} /> },
          ]}
        />
      </Panel>
    </div>
  );
}
