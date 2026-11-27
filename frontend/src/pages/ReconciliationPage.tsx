import { useEffect, useState } from "react";
import { apiFetch } from "../api/client";
import { apiPost, errorMessage } from "../api/resources";
import { can } from "../auth/permissions";
import { useAuth } from "../auth/AuthContext";
import { ErrorBanner, LoadingState, Notice, PageHeading } from "../components/Feedback";
import { Panel } from "../components/Panel";

type Recon = { id: string; provider: string; reference: string; amount: string; currency: string; status: string; exception_reason?: string };
type Summary = { count: number; unresolved_count: number; by_status: Record<string, number> };

export function ReconciliationPage() {
  const { user } = useAuth();
  const [rows, setRows] = useState<Recon[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ provider: "mock", reference: "", amount: "0.00", currency: "NGN" });

  const load = async () => {
    setLoading(true);
    try {
      const [list, sum] = await Promise.all([
        apiFetch<{ results?: Recon[] } | Recon[]>("/finance/reconciliation-records/"),
        apiFetch<Summary>("/finance/reconciliation-records/summary/"),
      ]);
      setRows(Array.isArray(list) ? list : list.results || []);
      setSummary(sum);
    } catch (e) { setError(errorMessage(e)); } finally { setLoading(false); }
  };
  useEffect(() => { void load(); }, []);

  const act = async (path: string, body?: Record<string, unknown>, msg?: string) => {
    setError(null); setNotice(null);
    try { await apiPost(path, body); setNotice(msg || "Done."); await load(); }
    catch (e) { setError(errorMessage(e)); }
  };

  if (!can(user, "finance", "view")) return <section className="card"><h2>Not available</h2></section>;
  return (
    <div className="page-stack">
      <PageHeading title="Reconciliation" description="Import, reconcile, and resolve finance reconciliation records." />
      <ErrorBanner message={error} /><Notice message={notice} />
      {summary ? <Panel title="Summary"><div className="grid"><div className="card metric"><p className="muted small">count</p><strong>{summary.count}</strong></div><div className="card metric"><p className="muted small">unresolved</p><strong>{summary.unresolved_count}</strong></div></div></Panel> : null}
      {can(user, "finance", "create") ? (
        <Panel title="Import record">
          <div className="form-grid">
            <label>Provider<input value={form.provider} onChange={(e) => setForm({ ...form, provider: e.target.value })} /></label>
            <label>Reference<input value={form.reference} onChange={(e) => setForm({ ...form, reference: e.target.value })} /></label>
            <label>Amount<input value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} /></label>
            <label>Currency<input value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })} /></label>
          </div>
          <button type="button" onClick={() => void act("/finance/reconciliation-records/import/", form, "Imported.")}>Import</button>
        </Panel>
      ) : null}
      <Panel title="Records">
        {loading ? <LoadingState /> : (
          <table className="data-table"><thead><tr><th>Provider</th><th>Reference</th><th>Amount</th><th>Status</th><th>Actions</th></tr></thead><tbody>
            {rows.map((r) => (
              <tr key={r.id}><td>{r.provider}</td><td>{r.reference}</td><td>{r.currency} {r.amount}</td><td>{r.status}</td><td>
                {can(user, "finance", "update") ? <><button type="button" className="secondary" onClick={() => void act(`/finance/reconciliation-records/${r.id}/reconcile/`, undefined, "Reconciled.")}>Reconcile</button>{" "}<button type="button" className="secondary" onClick={() => void act(`/finance/reconciliation-records/${r.id}/resolve/`, { reason: "manual_resolution" }, "Resolved.")}>Resolve</button></> : "-"}
              </td></tr>
            ))}
            {!rows.length ? <tr><td colSpan={5} className="muted">No records.</td></tr> : null}
          </tbody></table>
        )}
      </Panel>
    </div>
  );
}
