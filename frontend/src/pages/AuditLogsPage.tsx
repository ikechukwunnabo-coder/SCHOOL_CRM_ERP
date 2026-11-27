import { useEffect, useState } from "react";
import { apiFetch, apiFetchBlob, saveBlob } from "../api/client";
import { can } from "../auth/permissions";
import { useAuth } from "../auth/AuthContext";
import { ErrorBanner, LoadingState, PageHeading } from "../components/Feedback";
import { Panel } from "../components/Panel";

type AuditLog = { id: string; created_at: string; actor_email: string; action: string; target_type: string; target_id: string; reason: string };
type ListResp = { results?: AuditLog[] } | AuditLog[];

export function AuditLogsPage() {
  const { user } = useAuth();
  const [rows, setRows] = useState<AuditLog[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    apiFetch<ListResp>("/audit/logs/")
      .then((d) => setRows(Array.isArray(d) ? d : d.results || []))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const onExport = async () => {
    setBusy(true); setError(null);
    try { const { blob, filename } = await apiFetchBlob("/audit/logs/export-csv/", "audit-logs.csv"); saveBlob(blob, filename); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };

  if (!can(user, "audit", "view")) return <section className="card"><h2>Not available</h2></section>;
  return (
    <div className="page-stack">
      <PageHeading title="Audit logs" description="Scoped, read-only audit trail." actions={can(user, "audit", "export") ? <button className="secondary" disabled={busy} onClick={() => void onExport()} type="button">{busy ? "Exporting..." : "Export CSV"}</button> : undefined} />
      <ErrorBanner message={error} />
      <Panel title="Recent events">
        {loading ? <LoadingState /> : (
          <table className="data-table"><thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Target</th><th>Reason</th></tr></thead><tbody>
            {rows.map((r) => <tr key={r.id}><td>{r.created_at?.slice(0, 19).replace("T", " ")}</td><td>{r.actor_email || "-"}</td><td>{r.action}</td><td>{r.target_type} {r.target_id || ""}</td><td>{r.reason || "-"}</td></tr>)}
            {!rows.length ? <tr><td colSpan={5} className="muted">No audit events.</td></tr> : null}
          </tbody></table>
        )}
      </Panel>
    </div>
  );
}
