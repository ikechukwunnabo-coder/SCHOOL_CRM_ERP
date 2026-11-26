import { useEffect, useState } from "react";
import { apiFetch } from "../api/client";
import { can } from "../auth/permissions";
import { useAuth } from "../auth/AuthContext";
import { ErrorBanner, LoadingState, PageHeading } from "../components/Feedback";
import { Panel } from "../components/Panel";

type Dashboard = Record<string, unknown>;

function Metric({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="card metric">
      <p className="muted small">{label}</p>
      <strong>{typeof value === "object" ? JSON.stringify(value) : String(value ?? "-")}</strong>
    </div>
  );
}

function DashboardPanel({ title, path }: { title: string; path: string }) {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    apiFetch<Dashboard>(path).then(setData).catch((e: Error) => setError(e.message));
  }, [path]);
  if (error) return <ErrorBanner message={error} />;
  if (!data) return <LoadingState />;
  return (
    <Panel title={title}>
      <div className="grid">
        {Object.entries(data).flatMap(([k, v]) =>
          typeof v === "object" && v && !Array.isArray(v)
            ? Object.entries(v as Record<string, unknown>).map(([ik, iv]) => (
                <Metric key={`${k}-${ik}`} label={`${k}.${ik}`} value={iv} />
              ))
            : [<Metric key={k} label={k} value={v} />],
        )}
      </div>
    </Panel>
  );
}

export function OpsDashboardsPage() {
  const { user } = useAuth();
  const allowed = can(user, "finance", "view") || can(user, "accounting", "view") || can(user, "notifications", "view");
  if (!allowed) {
    return (
      <section className="card">
        <h2>Not available</h2>
        <p className="muted">Your role does not have access to this module.</p>
      </section>
    );
  }
  return (
    <div className="page-stack">
      <PageHeading title="Operations dashboards" description="Query-backed finance, accounting, and notification summaries." />
      {can(user, "finance", "view") ? <DashboardPanel title="Finance" path="/finance/dashboard/" /> : null}
      {can(user, "accounting", "view") ? <DashboardPanel title="Accounting" path="/accounting/dashboard/" /> : null}
      {can(user, "notifications", "view") ? <DashboardPanel title="Notifications" path="/notifications/dashboard/" /> : null}
    </div>
  );
}
