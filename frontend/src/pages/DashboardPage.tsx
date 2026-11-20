import { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { apiFetch } from "../api/client";

export function DashboardPage() {
  const { user, logout } = useAuth();
  const [health, setHealth] = useState<string>("checking...");

  useEffect(() => {
    apiFetch<{ status: string; database: string }>("/health/")
      .then((d) => setHealth(`${d.status} (db: ${d.database})`))
      .catch(() => setHealth("unavailable"));
  }, []);

  return (
    <div className="page">
      <header className="topbar">
        <div>
          <h2>Foundation Dashboard</h2>
          <p className="muted">Phase 1 scaffold — authenticated context</p>
        </div>
        <button onClick={() => void logout()}>Sign out</button>
      </header>
      <main className="grid">
        <section className="card">
          <h3>Current user</h3>
          <pre>{JSON.stringify(user, null, 2)}</pre>
        </section>
        <section className="card">
          <h3>API health</h3>
          <p>{health}</p>
        </section>
        <section className="card">
          <h3>Status</h3>
          <ul>
            <li>Auth: session/cookie baseline (D-011)</li>
            <li>RBAC/Audit: models & middleware stubs created</li>
            <li>Domain modules: pending (Phase 2+)</li>
          </ul>
        </section>
      </main>
    </div>
  );
}
