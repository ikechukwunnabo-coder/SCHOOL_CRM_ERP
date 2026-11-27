import { useEffect, useState } from "react";
import { apiFetch } from "../api/client";
import { apiPost, errorMessage } from "../api/resources";
import { can } from "../auth/permissions";
import { useAuth } from "../auth/AuthContext";
import { ErrorBanner, LoadingState, Notice, PageHeading } from "../components/Feedback";
import { Panel } from "../components/Panel";

type Page = { id: string; slug: string; title: string; status: string; is_public: boolean };

export function CmsAdminPage() {
  const { user } = useAuth();
  const [rows, setRows] = useState<Page[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ slug: "", title: "", body: "", status: "draft", is_public: true });

  const load = async () => {
    setLoading(true);
    try {
      const d = await apiFetch<{ results?: Page[] } | Page[]>("/cms/pages/");
      setRows(Array.isArray(d) ? d : d.results || []);
    } catch (e) { setError(errorMessage(e)); } finally { setLoading(false); }
  };
  useEffect(() => { void load(); }, []);

  const create = async () => {
    setError(null); setNotice(null);
    try { await apiPost("/cms/pages/", form); setNotice("Page created."); setForm({ slug: "", title: "", body: "", status: "draft", is_public: true }); await load(); }
    catch (e) { setError(errorMessage(e)); }
  };
  const publish = async (id: string) => {
    setError(null); setNotice(null);
    try { await apiPost(`/cms/pages/${id}/publish/`); setNotice("Published."); await load(); }
    catch (e) { setError(errorMessage(e)); }
  };

  if (!can(user, "cms", "view")) return <section className="card"><h2>Not available</h2></section>;
  return (
    <div className="page-stack">
      <PageHeading title="CMS pages" description="Manage public website pages." />
      <ErrorBanner message={error} /><Notice message={notice} />
      {can(user, "cms", "create") ? (
        <Panel title="Create page">
          <div className="form-grid">
            <label>Slug<input value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} /></label>
            <label>Title<input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></label>
            <label>Body<textarea value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} /></label>
          </div>
          <button type="button" onClick={() => void create()}>Create</button>
        </Panel>
      ) : null}
      <Panel title="Pages">
        {loading ? <LoadingState /> : (
          <table className="data-table"><thead><tr><th>Slug</th><th>Title</th><th>Status</th><th>Public</th><th>Action</th></tr></thead><tbody>
            {rows.map((r) => <tr key={r.id}><td>{r.slug}</td><td>{r.title}</td><td>{r.status}</td><td>{String(r.is_public)}</td><td>{can(user, "cms", "publish") ? <button type="button" className="secondary" onClick={() => void publish(r.id)}>Publish</button> : "-"}</td></tr>)}
            {!rows.length ? <tr><td colSpan={5} className="muted">No pages.</td></tr> : null}
          </tbody></table>
        )}
      </Panel>
    </div>
  );
}
