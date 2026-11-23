import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "../api/client";
import { can, roleNames } from "../auth/permissions";
import { useAuth } from "../auth/AuthContext";
import { PageHeading } from "../components/Feedback";
import { Panel } from "../components/Panel";

const LINKS = [
  { to: "/academics/calendar", label: "Academic calendar", module: "academics" },
  { to: "/academics/timetable", label: "Timetable", module: "teaching" },
  { to: "/teaching/workload", label: "Teacher workload", module: "teaching" },
  { to: "/attendance/students", label: "Student attendance", module: "attendance" },
  { to: "/attendance/teachers", label: "Teacher attendance", module: "attendance" },
  { to: "/examinations/results", label: "Results workflow", module: "examinations" },
  { to: "/examinations/report-cards", label: "Report cards", module: "examinations" },
  { to: "/transcripts", label: "Transcripts", module: "transcripts" },
] as const;

export function DashboardPage() {
  const { user } = useAuth();
  const [health, setHealth] = useState("checking...");

  useEffect(() => {
    apiFetch<{ status: string; database: string }>("/health/")
      .then((data) => setHealth(`${data.status} (db: ${data.database})`))
      .catch(() => setHealth("unavailable"));
  }, []);

  const available = LINKS.filter((link) => can(user, link.module, "view"));

  return (
    <div className="page-stack">
      <PageHeading title="School operations" description="Academic, attendance, examination, and transcript workflows for your role." />
      <div className="grid">
        <Panel title="Signed-in user">
          <p>{user?.email}</p>
          <p className="muted small">{roleNames(user).join(", ") || "No active roles"}</p>
          <p className="muted small">Institution: {user?.institution || "not set"}</p>
        </Panel>
        <Panel title="API health">
          <p>{health}</p>
        </Panel>
      </div>
      <Panel title="Available workflows">
        <div className="link-grid">
          {available.map((link) => (
            <Link key={link.to} to={link.to} className="workflow-link">
              {link.label}
            </Link>
          ))}
        </div>
      </Panel>
    </div>
  );
}
