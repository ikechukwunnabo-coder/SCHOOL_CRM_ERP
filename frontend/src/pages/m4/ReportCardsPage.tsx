import { useAuth } from "../../auth/AuthContext";
import { can } from "../../auth/permissions";
import { apiFetchBlob, saveBlob } from "../../api/client";
import { apiPost, optionLabel, shortDate, text, type Entity } from "../../api/resources";
import { DataTable } from "../../components/DataTable";
import { ErrorBanner, LoadingState, Notice, PageHeading, StatusBadge } from "../../components/Feedback";
import { SelectField } from "../../components/FormControls";
import { Panel } from "../../components/Panel";
import { useAction } from "../../hooks/useAction";
import { useApiList } from "../../hooks/useApiResource";
import { useForm } from "../../hooks/useForm";

export function ReportCardsPage() {
  const { user } = useAuth();
  const cards = useApiList<Entity>("/examinations/report-cards/");
  const students = useApiList<Entity>("/students/");
  const sessions = useApiList<Entity>("/academic-sessions/");
  const terms = useApiList<Entity>("/terms/");
  const action = useAction();
  const canGenerate = can(user, "examinations", "create");
  const canDownload = can(user, "examinations", "print");
  const form = useForm({ student: "", session: "", term: "" });

  const studentOptions = students.data.map((item) => ({
    value: item.id,
    label: `${text(item.admission_number)} ${text(item.first_name, "")} ${text(item.last_name, "")}`.trim(),
  }));
  const sessionOptions = sessions.data.map((item) => ({ value: item.id, label: optionLabel(item) }));
  const termOptions = terms.data.map((item) => ({ value: item.id, label: optionLabel(item) }));
  const labelFor = (options: { value: string; label: string }[], id: unknown) => options.find((option) => option.value === id)?.label || text(id);

  const generate = (event: React.FormEvent) => {
    event.preventDefault();
    void action.run(
      () =>
        apiPost<Entity>("/examinations/report-cards/generate/", {
          student: form.values.student,
          session: form.values.session,
          term: form.values.term || undefined,
        }),
      () => {
        cards.reload();
        return "Report card generated.";
      },
    );
  };

  const download = (id: string, reference: string) => {
    void action.run(
      () => apiFetchBlob(`/examinations/report-cards/${id}/download/`, `${reference || "report-card"}.pdf`),
      (file) => {
        saveBlob(file.blob, file.filename);
        return `Downloaded ${file.filename}.`;
      },
    );
  };

  return (
    <div className="page-stack">
      <PageHeading title="Report cards" description="Generate snapshots from published results and download the PDF copy." />
      <ErrorBanner message={action.error || cards.error || students.error || sessions.error || terms.error} />
      <Notice message={action.notice} />

      {canGenerate ? (
        <Panel title="Generate report card" description="Generation is limited to students with published results for the selected session.">
          <form className="form" onSubmit={generate}>
            <SelectField label="Student" value={form.values.student} onChange={(value) => form.setField("student", value)} options={studentOptions} required />
            <div className="form-row">
              <SelectField label="Academic session" value={form.values.session} onChange={(value) => form.setField("session", value)} options={sessionOptions} required />
              <SelectField label="Term" value={form.values.term} onChange={(value) => form.setField("term", value)} options={termOptions} />
            </div>
            <button type="submit" disabled={action.busy}>Generate report card</button>
          </form>
        </Panel>
      ) : (
        <Panel title="Read-only access" description="Your role can view report cards but cannot generate them." />
      )}

      <Panel title="Generated report cards">
        {cards.loading ? <LoadingState /> : null}
        <DataTable
          rows={cards.data}
          columns={[
            { key: "reference", label: "Reference", render: (row) => text(row.reference) },
            { key: "student", label: "Student", render: (row) => labelFor(studentOptions, row.student) },
            { key: "session", label: "Session", render: (row) => labelFor(sessionOptions, row.session) },
            { key: "term", label: "Term", render: (row) => (row.term ? labelFor(termOptions, row.term) : "Full session") },
            { key: "version", label: "Version", render: (row) => text(row.version) },
            { key: "generated", label: "Published", render: (row) => shortDate(row.published_at) },
            { key: "status", label: "Status", render: (row) => <StatusBadge value={row.status} /> },
            {
              key: "actions",
              label: "Actions",
              render: (row) =>
                canDownload ? (
                  <button type="button" className="small-button" disabled={action.busy} onClick={() => download(row.id, text(row.reference))}>
                    Download PDF
                  </button>
                ) : (
                  <span className="muted">-</span>
                ),
            },
          ]}
        />
      </Panel>
    </div>
  );
}
