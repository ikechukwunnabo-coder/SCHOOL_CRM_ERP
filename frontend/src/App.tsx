import { Navigate, Route, Routes } from "react-router-dom";
import "./App.css";
import { useAuth } from "./auth/AuthContext";
import { AppShell } from "./components/AppShell";
import { RequirePermission } from "./components/RequirePermission";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { OpsDashboardsPage } from "./pages/OpsDashboardsPage";
import { ReconciliationPage } from "./pages/ReconciliationPage";
import { AuditLogsPage } from "./pages/AuditLogsPage";
import { TeacherPortalPage } from "./pages/TeacherPortalPage";
import { AcademicCalendarPage } from "./pages/m3/AcademicCalendarPage";
import { StudentAttendancePage } from "./pages/m3/StudentAttendancePage";
import { TeacherAttendancePage } from "./pages/m3/TeacherAttendancePage";
import { TeacherWorkloadPage } from "./pages/m3/TeacherWorkloadPage";
import { TimetablePage } from "./pages/m3/TimetablePage";
import { ReportCardsPage } from "./pages/m4/ReportCardsPage";
import { ResultsPage } from "./pages/m4/ResultsPage";
import { TranscriptsPage } from "./pages/m4/TranscriptsPage";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="page">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route
          path="academics/calendar"
          element={
            <RequirePermission module="academics">
              <AcademicCalendarPage />
            </RequirePermission>
          }
        />
        <Route
          path="academics/timetable"
          element={
            <RequirePermission module="teaching">
              <TimetablePage />
            </RequirePermission>
          }
        />
        <Route
          path="teaching/workload"
          element={
            <RequirePermission module="teaching">
              <TeacherWorkloadPage />
            </RequirePermission>
          }
        />
        <Route
          path="attendance/students"
          element={
            <RequirePermission module="attendance">
              <StudentAttendancePage />
            </RequirePermission>
          }
        />
        <Route
          path="attendance/teachers"
          element={
            <RequirePermission module="attendance">
              <TeacherAttendancePage />
            </RequirePermission>
          }
        />
        <Route
          path="examinations/results"
          element={
            <RequirePermission module="examinations">
              <ResultsPage />
            </RequirePermission>
          }
        />
        <Route
          path="examinations/report-cards"
          element={
            <RequirePermission module="examinations">
              <ReportCardsPage />
            </RequirePermission>
          }
        />
        <Route
          path="transcripts"
          element={
            <RequirePermission module="transcripts">
              <TranscriptsPage />
            </RequirePermission>
          }
        />
        <Route
          path="operations/dashboards"
          element={<OpsDashboardsPage />}
        />
        <Route
          path="operations/reconciliation"
          element={
            <RequirePermission module="finance">
              <ReconciliationPage />
            </RequirePermission>
          }
        />
        <Route
          path="operations/audit-logs"
          element={
            <RequirePermission module="audit">
              <AuditLogsPage />
            </RequirePermission>
          }
        />
        <Route
          path="portal/teacher"
          element={
            <RequirePermission module="teaching">
              <TeacherPortalPage />
            </RequirePermission>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
