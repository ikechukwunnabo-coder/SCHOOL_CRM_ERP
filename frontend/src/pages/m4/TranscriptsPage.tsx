import { useState } from "react";
import { useAuth } from "../../auth/AuthContext";
import { can } from "../../auth/permissions";
import { apiFetchBlob, saveBlob } from "../../api/client";
import { apiPost, text, type Entity } from "../../api/resources";
import { DataTable } from "../../components/DataTable";
import { ErrorBanner, LoadingState, Notice, PageHeading, StatusBadge } from "../../components/Feedback";
import { SelectField, TextAreaField, TextField } from "../../components/FormControls";
import { Panel } from "../../components/Panel";
import { useAction } from "../../hooks/useAction";
import { useApiList } from "../../hooks/useApiResource";
import { useForm } from "../../hooks/useForm";

type TokenResult = Entity & { verification_token?: string };

type VerificationResult = {
  valid: boolean;
  status: string;
  checked_at: string;
  institution?: { name: string; code: string };
  reference_number?: string;
  version?: number;
  kind?: string;
};

export function TranscriptsPage() {
  const { user } = useAuth();
  const requests = useApiList<Entity>("/transcripts/requests/");
  const transcripts = useApiList<Entity>("/transcripts/");
  const students = useApiList<Entity>("/students/");
  const action = useAction();
  const canCreate = can(user, "transcripts", "create");
  const canReview = can(user, "transcripts", "review");
  const canApprove = can(user, "transcripts", "approve");
  const canIssue = can(user, "transcripts", "issue_or_revoke");
  const canUpdate = can(user, "transcripts", "update");
  const canDownload = can(user, "transcripts", "download");
  const requestForm = useForm({ student: "", purpose: "", requestedKind: "official" });
  const decisionForm = useForm({ request: "", reason: "" });
  const issueForm = useForm({ transcript: "", issuedTo: "", purpose: "" });
  const reasonForm = useForm({ transcript: "", reason: "" });
  const verifyForm = useForm({ token: "" });
  const [token, setToken] = useState<string | null>(null);
  const [verification, setVerification] = useState<VerificationResult | null>(null);

  const studentOptions = students.data.map((item) => ({
    value: item.id,
    label: `${text(item.admission_number)} ${text(item.first_name, "")} ${text(item.last_name, "")}`.trim(),
  }));
  const studentName = (id: unknown) => studentOptions.find((option) => option.value === id)?.label || text(id);
  const requestOptions = requests.data.map((item) => ({
    value: item.id,
    label: `${studentName(item.student)} / ${text(item.status)}`,
  }));
  const transcriptOptions = transcripts.data.map((item) => ({
    value: item.id,
    label: `${text(item.reference_number)} v${text(item.version)} / ${text(item.status)}`,
  }));

  const createRequest = (event: React.FormEvent) => {
    event.preventDefault();
    void action.run(
      () =>
        apiPost<Entity>("/transcripts/requests/", {
          student: requestForm.values.student,
          purpose: requestForm.values.purpose,
          requested_kind: requestForm.values.requestedKind,
        }),
      () => {
        requests.reload();
        requestForm.reset();
        return "Transcript request submitted.";
      },
    );
  };

  const requestAction = (path: "review" | "approve" | "reject" | "generate") => {
    void action.run(
      () => apiPost<TokenResult>(`/transcripts/requests/${decisionForm.values.request}/${path}/`, path === "generate" ? {} : { reason: decisionForm.values.reason }),
      (result) => {
        requests.reload();
        transcripts.reload();
        if (result.verification_token) setToken(result.verification_token);
        return `Request ${path} completed.`;
      },
    );
  };

  const issue = (event: React.FormEvent) => {
    event.preventDefault();
    void action.run(
      () =>
        apiPost<Entity>(`/transcripts/${issueForm.values.transcript}/issue/`, {
          issued_to: issueForm.values.issuedTo,
          purpose: issueForm.values.purpose,
        }),
      () => {
        transcripts.reload();
        requests.reload();
        return "Transcript issued.";
      },
    );
  };

  const correct = (event: React.FormEvent) => {
    event.preventDefault();
    void action.run(
      () => apiPost<TokenResult>(`/transcripts/${reasonForm.values.transcript}/correct/`, { reason: reasonForm.values.reason }),
      (result) => {
        transcripts.reload();
        if (result.verification_token) setToken(result.verification_token);
        reasonForm.reset();
        return "Corrected transcript created.";
      },
    );
  };

  const revoke = () => {
    void action.run(
      () => apiPost<Entity>(`/transcripts/${reasonForm.values.transcript}/revoke/`, { reason: reasonForm.values.reason }),
      () => {
        transcripts.reload();
        reasonForm.reset();
        return "Transcript revoked.";
      },
    );
  };

  const download = (id: string, reference: string) => {
    void action.run(
      () => apiFetchBlob(`/transcripts/${id}/download/`, `${reference || "transcript"}.pdf`),
      (file) => {
        saveBlob(file.blob, file.filename);
        return `Downloaded ${file.filename}.`;
      },
    );
  };

  const verify = (event: React.FormEvent) => {
    event.preventDefault();
    void action.run(
      () => apiPost<VerificationResult>("/transcripts/verify/", { token: verifyForm.values.token }),
      (result) => {
        setVerification(result);
        return result.valid ? "Token is valid." : `Verification outcome: ${result.status.replace(/_/g, " ")}.`;
      },
    );
  };

  return (
    <div className="page-stack">
      <PageHeading title="Transcripts" description="Request, review, issue, download, and verify official transcripts." />
      <ErrorBanner message={action.error || requests.error || transcripts.error || students.error} />
      <Notice message={action.notice} />

      <div className="grid">
        {canCreate ? (
          <Panel title="Request transcript" description="Requests are scoped to the signed-in institution.">
            <form className="form" onSubmit={createRequest}>
              <SelectField label="Student" value={requestForm.values.student} onChange={(value) => requestForm.setField("student", value)} options={studentOptions} required />
              <TextAreaField label="Purpose" value={requestForm.values.purpose} onChange={(value) => requestForm.setField("purpose", value)} required />
              <SelectField label="Kind" value={requestForm.values.requestedKind} onChange={(value) => requestForm.setField("requestedKind", value)} options={[{ value: "official", label: "Official" }, { value: "provisional", label: "Provisional" }]} required />
              <button type="submit" disabled={action.busy}>Submit request</button>
            </form>
          </Panel>
        ) : null}
        <Panel title="Verify a transcript" description="Checks the token issued when a transcript was generated or corrected.">
          <form className="form" onSubmit={verify}>
            <TextField label="Verification token" value={verifyForm.values.token} onChange={(value) => verifyForm.setField("token", value)} required />
            <button type="submit" disabled={action.busy}>Verify token</button>
          </form>
          {verification ? (
            <dl className="result-list">
              <dt>Outcome</dt>
              <dd>{verification.status.replace(/_/g, " ")}</dd>
              <dt>Reference</dt>
              <dd>{text(verification.reference_number)}</dd>
              <dt>Version</dt>
              <dd>{text(verification.version)}</dd>
              <dt>Institution</dt>
              <dd>{verification.institution ? text(verification.institution.name) : "-"}</dd>
            </dl>
          ) : null}
        </Panel>
        {token ? (
          <Panel title="Latest verification token" description="Copy it now; the raw token is shown only when generated.">
            <code className="token-value">{token}</code>
          </Panel>
        ) : null}
      </div>

      {canReview || canApprove || canCreate ? (
        <Panel title="Request decisions" description="Review, approve, reject, and generate transcript documents.">
          <div className="decision-grid">
            <SelectField label="Request" value={decisionForm.values.request} onChange={(value) => decisionForm.setField("request", value)} options={requestOptions} />
            <TextAreaField label="Reason" value={decisionForm.values.reason} onChange={(value) => decisionForm.setField("reason", value)} />
            <div className="row-actions">
              {canReview ? (
                <>
                  <button type="button" className="small-button" disabled={action.busy || !decisionForm.values.request} onClick={() => requestAction("review")}>Review request</button>
                  <button type="button" className="small-button secondary" disabled={action.busy || !decisionForm.values.request} onClick={() => requestAction("reject")}>Reject request</button>
                </>
              ) : null}
              {canApprove ? (
                <button type="button" className="small-button" disabled={action.busy || !decisionForm.values.request} onClick={() => requestAction("approve")}>Approve request</button>
              ) : null}
              {canCreate ? (
                <button type="button" className="small-button" disabled={action.busy || !decisionForm.values.request} onClick={() => requestAction("generate")}>Generate transcript</button>
              ) : null}
            </div>
          </div>
        </Panel>
      ) : null}

      <Panel title="Transcript requests">
        {requests.loading ? <LoadingState /> : null}
        <DataTable
          rows={requests.data}
          columns={[
            { key: "student", label: "Student", render: (row) => studentName(row.student) },
            { key: "kind", label: "Kind", render: (row) => text(row.requested_kind) },
            { key: "purpose", label: "Purpose", render: (row) => text(row.purpose) },
            { key: "status", label: "Status", render: (row) => <StatusBadge value={row.status} /> },
            { key: "reason", label: "Decision reason", render: (row) => text(row.decision_reason) },
          ]}
        />
      </Panel>

      {canIssue || canUpdate ? (
        <div className="grid">
          {canIssue ? (
            <Panel title="Issue transcript">
              <form className="form" onSubmit={issue}>
                <SelectField label="Transcript" value={issueForm.values.transcript} onChange={(value) => issueForm.setField("transcript", value)} options={transcriptOptions} required />
                <TextField label="Issued to" value={issueForm.values.issuedTo} onChange={(value) => issueForm.setField("issuedTo", value)} required />
                <TextField label="Purpose" value={issueForm.values.purpose} onChange={(value) => issueForm.setField("purpose", value)} />
                <button type="submit" disabled={action.busy}>Issue transcript</button>
              </form>
            </Panel>
          ) : null}
          <Panel title="Corrections and revocation">
            <form className="form" onSubmit={correct}>
              <SelectField label="Transcript" value={reasonForm.values.transcript} onChange={(value) => reasonForm.setField("transcript", value)} options={transcriptOptions} required />
              <TextAreaField label="Reason" value={reasonForm.values.reason} onChange={(value) => reasonForm.setField("reason", value)} required />
              <div className="row-actions">
                {canUpdate ? <button type="submit" disabled={action.busy}>Create correction</button> : null}
                {canIssue ? <button type="button" className="small-button secondary" disabled={action.busy} onClick={revoke}>Revoke transcript</button> : null}
              </div>
            </form>
          </Panel>
        </div>
      ) : null}

      <Panel title="Transcripts">
        {transcripts.loading ? <LoadingState /> : null}
        <DataTable
          rows={transcripts.data}
          columns={[
            { key: "reference", label: "Reference", render: (row) => text(row.reference_number) },
            { key: "student", label: "Student", render: (row) => studentName(row.student) },
            { key: "kind", label: "Kind", render: (row) => text(row.kind) },
            { key: "version", label: "Version", render: (row) => text(row.version) },
            { key: "issued", label: "Issued to", render: (row) => text(row.issued_to) },
            { key: "status", label: "Status", render: (row) => <StatusBadge value={row.status} /> },
            {
              key: "actions",
              label: "Actions",
              render: (row) =>
                canDownload && row.status === "issued" ? (
                  <button type="button" className="small-button" disabled={action.busy} onClick={() => download(row.id, text(row.reference_number))}>
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
