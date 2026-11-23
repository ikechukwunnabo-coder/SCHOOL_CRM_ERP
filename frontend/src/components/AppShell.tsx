import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { can, roleNames, type ModuleKey } from "../auth/permissions";
import { ErrorBanner } from "./Feedback";

type NavItem = { to: string; label: string; module?: ModuleKey };

const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Dashboard" },
  { to: "/academics/calendar", label: "Academic calendar", module: "academics" },
  { to: "/academics/timetable", label: "Timetable", module: "teaching" },
  { to: "/teaching/workload", label: "Teacher workload", module: "teaching" },
  { to: "/attendance/students", label: "Student attendance", module: "attendance" },
  { to: "/attendance/teachers", label: "Teacher attendance", module: "attendance" },
  { to: "/examinations/results", label: "Results workflow", module: "examinations" },
  { to: "/examinations/report-cards", label: "Report cards", module: "examinations" },
  { to: "/transcripts", label: "Transcripts", module: "transcripts" },
];

export function AppShell() {
  const { user, logout, error } = useAuth();
  const navigate = useNavigate();
  const visible = NAV_ITEMS.filter((item) => !item.module || can(user, item.module, "view"));

  const signOut = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">School CRM &amp; ERP</div>
        <nav aria-label="Main navigation">
          {visible.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="main-column">
        <header className="topbar">
          <div>
            <p className="muted small">Signed in as</p>
            <strong>{user?.email}</strong>
            <p className="muted small">{roleNames(user).join(", ") || "No active roles"}</p>
          </div>
          <button type="button" className="secondary" onClick={() => void signOut()}>
            Sign out
          </button>
        </header>
        <main className="content">
          <ErrorBanner message={error} />
          <Outlet />
        </main>
      </div>
    </div>
  );
}
