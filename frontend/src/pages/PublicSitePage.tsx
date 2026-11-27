import { useEffect, useState } from "react";
import { apiFetch } from "../api/client";
import { PageHeading, LoadingState, ErrorBanner } from "../components/Feedback";
import { Panel } from "../components/Panel";

type Page = { slug: string; title: string; body: string };

export function PublicSitePage() {
  const [rows, setRows] = useState<Page[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const inst = new URLSearchParams(window.location.search).get("institution");
    const q = inst ? `?institution=${encodeURIComponent(inst)}` : "";
    apiFetch<Page[]>(`/cms/public/pages/${q}`)
      .then(setRows).catch((e: Error) => setError(e.message)).finally(() => setLoading(false));
  }, []);
  return (
    <div className="page-stack">
      <PageHeading title="Public website" description="Published public CMS content." />
      <ErrorBanner message={error} />
      <Panel title="Pages">
        {loading ? <LoadingState /> : rows.map((p) => <article key={p.slug} className="card"><h3>{p.title}</h3><p>{p.body}</p></article>)}
        {!loading && !rows.length ? <p className="muted">No published pages.</p> : null}
      </Panel>
    </div>
  );
}
