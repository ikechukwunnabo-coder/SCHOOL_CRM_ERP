import { useState } from "react";
import { useAuth } from "../../auth/AuthContext";
import { can } from "../../auth/permissions";
import { apiPost, optionLabel, text, type Entity } from "../../api/resources";
import { DataTable } from "../../components/DataTable";
import { ErrorBanner, LoadingState, Notice, PageHeading, StatusBadge } from "../../components/Feedback";
import { SelectField, TextAreaField, TextField } from "../../components/FormControls";
import { Panel } from "../../components/Panel";
import { useAction } from "../../hooks/useAction";
import { useApiList } from "../../hooks/useApiResource";
import { useForm } from "../../hooks/useForm";

type ScoreValues = Record<string, string>;

function ScoreFields({ components, values, onChange }: { components: Entity[]; values: ScoreValues; onChange: (code: string, value: string) => void }) {
  if (!components.length) return <p className="muted small">Select a scheme with assessment components.</p>;
  return (
    <div className="score-grid">
      {components.map((component) => (
        <TextField
          key={component.id}
          label={`${text(component.code)} (max ${text(component.max_marks)})`}
          type="number"
          min="0"
          step="0.01"
          value={values[text(component.code)] || ""}
          onChange={(value) => onChange(text(component.code), value)}
          required
        />
      ))}
    </div>
  );
}

export function ResultsPage() {
  const { user } = useAuth();
  const results = useApiList<Entity>("/examinations/results/");
  const schemes = useApiList<Entity>("/examinations/assessment-schemes/");
  const components = useApiList<Entity>("/examinations/assessment-components/");
  const offerings = useApiList<Entity>("/subject-offerings/");
  const students = useApiList<Entity>("/students/");
  const subjects = useApiList<Entity>("/subjects/");
  const action = useAction();
  const canRecord = can(user, "examinations", "create");
  const canReview = can(user, "examinations", "review");
  const canApprove = can(user, "examinations", "approve");
  const canPublish = can(user, "examinations", "publish");
  const recordForm = useForm({ scheme: "", offering: "", student: "" });
  const submitForm = useForm({ scheme: "", offering: "" });
  const returnForm = useForm({ result: "", reason: "" });
  const correctionForm = useForm({ result: "", reason: "" });
  const [recordScores, setRecordScores] = useState<ScoreValues>({});
  const [correctionScores, setCorrectionScores] = useState<ScoreValues>({});

  const schemeOptions = schemes.data.map((item) => ({ value: item.id, label: optionLabel(item) }));
  const offeringOptions = offerings.data.map((item) => {
    const subject = subjects.data.find((entry) => entry.id === item.subject);
    return { value: item.id, label: subject ? optionLabel(subject) : text(item.id) };
  });
  const studentOptions = students.data.map((item) => ({
    value: item.id,
    label: `${text(item.admission_number)} ${text(item.first_name, "")} ${text(item.last_name, "")}`.trim(),
  }));
  const resultOptions = results.data.map((item) => ({
    value: item.id,
    label: `${studentOptions.find((option) => option.value === item.student)?.label || text(item.student)} / ${offeringOptions.find((option) => option.value === item.offering)?.label || text(item.offering)}`,
  }));
  const studentName = (id: unknown) => studentOptions.find((option) => option.value === id)?.label || text(id);
  const offeringName = (id: unknown) => offeringOptions.find((option) => option.value === id)?.label || text(id);
  const schemeName = (id: unknown) => schemeOptions.find((option) => option.value === id)?.label || text(id);
  const componentsFor = (schemeId: string) => components.data.filter((component) => component.scheme === schemeId);
  const numericScores = (values: ScoreValues) =>
    Object.fromEntries(
      Object.entries(values)
        .filter(([, value]) => value !== "")
        .map(([code, value]) => [code, Number(value)]),
    );

  const record = (event: React.FormEvent) => {
    event.preventDefault();
    void action.run(
      () =>
        apiPost<Entity>("/examinations/results/", {
          scheme: recordForm.values.scheme,
          offering: recordForm.values.offering,
          student: recordForm.values.student,
          component_scores: numericScores(recordScores),
        }),
      () => {
        results.reload();
        setRecordScores({});
        return "Result recorded as draft.";
      },
    );
  };

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    void action.run(
      () => apiPost<{ submitted: number }>("/examinations/results/submit/", { scheme: submitForm.values.scheme, offering: submitForm.values.offering }),
      (result) => {
        results.reload();
        return `${text(result.submitted, "0")} result(s) submitted.`;
      },
    );
  };

  const transition = (id: string, path: string, body: Record<string, unknown>, message: string) => {
    void action.run(
      () => apiPost<Entity>(`/examinations/results/${id}/${path}/`, body),
      () => {
        results.reload();
        return message;
      },
    );
  };

  const correct = (event: React.FormEvent) => {
    event.preventDefault();
    void action.run(
      () =>
        apiPost<Entity>(`/examinations/results/${correctionForm.values.result}/correct/`, {
          component_scores: numericScores(correctionScores),
          reason: correctionForm.values.reason,
        }),
      () => {
        correctionForm.reset();
        setCorrectionScores({});
        results.reload();
        return "Correction submitted for re-approval.";
      },
    );
  };

  const correctionResult = results.data.find((item) => item.id === correctionForm.values.result);
  const correctionComponents = componentsFor(text(correctionResult?.scheme));

  return (
    <div className="page-stack">
      <PageHeading title="Results workflow" description="Record marks, submit an offering, then review, approve, publish, or correct results." />
      <ErrorBanner message={action.error || results.error || schemes.error || components.error || offerings.error || students.error} />
      <Notice message={action.notice} />

      {canRecord ? (
        <div className="grid">
          <Panel title="Record result" description="Scores use the assessment component codes defined on the scheme.">
            <form className="form" onSubmit={record}>
              <SelectField label="Assessment scheme" value={recordForm.values.scheme} onChange={(value) => { recordForm.setField("scheme", value); setRecordScores({}); }} options={schemeOptions} required />
              <SelectField label="Subject offering" value={recordForm.values.offering} onChange={(value) => recordForm.setField("offering", value)} options={offeringOptions} required />
              <SelectField label="Student" value={recordForm.values.student} onChange={(value) => recordForm.setField("student", value)} options={studentOptions} required />
              <ScoreFields components={componentsFor(recordForm.values.scheme)} values={recordScores} onChange={(code, value) => setRecordScores({ ...recordScores, [code]: value })} />
              <button type="submit" disabled={action.busy}>Record result</button>
            </form>
          </Panel>
          <Panel title="Submit results" description="Submits every recorded result for a scheme and offering.">
            <form className="form" onSubmit={submit}>
              <SelectField label="Assessment scheme" value={submitForm.values.scheme} onChange={(value) => submitForm.setField("scheme", value)} options={schemeOptions} required />
              <SelectField label="Subject offering" value={submitForm.values.offering} onChange={(value) => submitForm.setField("offering", value)} options={offeringOptions} required />
              <button type="submit" disabled={action.busy}>Submit results</button>
            </form>
          </Panel>
        </div>
      ) : (
        <Panel title="Read-only access" description="Your role can review results but cannot record or submit them." />
      )}

      {canReview || canApprove ? (
        <div className="grid">
          {canReview ? (
            <Panel title="Return for correction" description="Requires a reason and moves a submitted result back to the teacher.">
              <form className="form" onSubmit={(event) => { event.preventDefault(); transition(returnForm.values.result, "return-for-correction", { reason: returnForm.values.reason }, "Result returned for correction."); }}>
                <SelectField label="Result" value={returnForm.values.result} onChange={(value) => returnForm.setField("result", value)} options={resultOptions} required />
                <TextAreaField label="Reason" value={returnForm.values.reason} onChange={(value) => returnForm.setField("reason", value)} required />
                <button type="submit" disabled={action.busy}>Return for correction</button>
              </form>
            </Panel>
          ) : null}
          {canApprove ? (
            <Panel title="Correct approved result" description="Corrected results return to submitted status for re-approval.">
              <form className="form" onSubmit={correct}>
                <SelectField label="Result" value={correctionForm.values.result} onChange={(value) => { correctionForm.setField("result", value); setCorrectionScores({}); }} options={resultOptions} required />
                <ScoreFields components={correctionComponents} values={correctionScores} onChange={(code, value) => setCorrectionScores({ ...correctionScores, [code]: value })} />
                <TextAreaField label="Reason" value={correctionForm.values.reason} onChange={(value) => correctionForm.setField("reason", value)} required />
                <button type="submit" disabled={action.busy}>Submit correction</button>
              </form>
            </Panel>
          ) : null}
        </div>
      ) : null}

      <Panel title="Result records">
        {results.loading ? <LoadingState /> : null}
        <DataTable
          rows={results.data}
          columns={[
            { key: "student", label: "Student", render: (row) => studentName(row.student) },
            { key: "offering", label: "Offering", render: (row) => offeringName(row.offering) },
            { key: "scheme", label: "Scheme", render: (row) => schemeName(row.scheme) },
            { key: "total", label: "Total", render: (row) => text(row.total_score) },
            { key: "grade", label: "Grade", render: (row) => text(row.grade) },
            { key: "status", label: "Status", render: (row) => <StatusBadge value={row.status} /> },
            {
              key: "actions",
              label: "Workflow",
              render: (row) => (
                <div className="row-actions">
                  {canApprove && row.status === "submitted" ? (
                    <button type="button" className="small-button" disabled={action.busy} onClick={() => transition(row.id, "approve", {}, "Result approved.")}>
                      Approve
                    </button>
                  ) : null}
                  {canPublish && row.status === "approved" ? (
                    <button type="button" className="small-button" disabled={action.busy} onClick={() => transition(row.id, "publish", {}, "Result published.")}>
                      Publish
                    </button>
                  ) : null}
                </div>
              ),
            },
          ]}
        />
      </Panel>
    </div>
  );
}
