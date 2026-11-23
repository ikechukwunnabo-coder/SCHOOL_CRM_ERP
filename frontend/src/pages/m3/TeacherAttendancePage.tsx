import { useAuth } from "../../auth/AuthContext";
import { can } from "../../auth/permissions";
import { apiPost, text, type Entity } from "../../api/resources";
import { DataTable } from "../../components/DataTable";
import { ErrorBanner, LoadingState, Notice, PageHeading, StatusBadge } from "../../components/Feedback";
import { SelectField, TextField } from "../../components/FormControls";
import { Panel } from "../../components/Panel";
import { useAction } from "../../hooks/useAction";
import { useApiList } from "../../hooks/useApiResource";
import { useForm } from "../../hooks/useForm";

const STATUS_OPTIONS = [
  { value: "present", label: "Present" },
  { value: "absent", label: "Absent" },
  { value: "late", label: "Late" },
  { value: "excused", label: "Excused" },
];

export function TeacherAttendancePage() {
  const { user } = useAuth();
  const employees = useApiList<Entity>("/employees/");
  const action = useAction();
  const canMark = can(user, "attendance", "create");
  const canApprove = can(user, "attendance", "approve");
  const filterForm = useForm({ employee: "", dateFrom: "", dateTo: "", status: "" });
  const markForm = useForm({ employee: "", attendanceDate: "", status: "present" });

  const query = new URLSearchParams();
  if (filterForm.values.employee) query.set("employee", filterForm.values.employee);
  if (filterForm.values.dateFrom) query.set("date_from", filterForm.values.dateFrom);
  if (filterForm.values.dateTo) query.set("date_to", filterForm.values.dateTo);
  if (filterForm.values.status) query.set("status", filterForm.values.status);
  const records = useApiList<Entity>(`/teacher-attendance/query/?${query.toString()}`);
  const employeeOptions = employees.data.map((item) => ({
    value: item.id,
    label: `${text(item.employee_number)} ${text(item.first_name, "")} ${text(item.last_name, "")}`.trim(),
  }));
  const employeeName = (id: unknown) => employeeOptions.find((option) => option.value === id)?.label || text(id);

  const mark = (event: React.FormEvent) => {
    event.preventDefault();
    void action.run(
      () =>
        apiPost<Entity>("/teacher-attendance/mark/", {
          employee: markForm.values.employee,
          attendance_date: markForm.values.attendanceDate,
          status: markForm.values.status,
        }),
      () => {
        records.reload();
        return "Teacher attendance recorded.";
      },
    );
  };

  const approve = (id: string) => {
    void action.run(
      () => apiPost<Entity>(`/teacher-attendance/${id}/approve/`),
      () => {
        records.reload();
        return "Attendance approved.";
      },
    );
  };

  return (
    <div className="page-stack">
      <PageHeading title="Teacher attendance" description="Query, mark, and approve employee attendance records." />
      <ErrorBanner message={action.error || records.error || employees.error} />
      <Notice message={action.notice} />

      {canMark ? (
        <Panel title="Mark teacher attendance">
          <form className="form" onSubmit={mark}>
            <SelectField label="Teacher" value={markForm.values.employee} onChange={(value) => markForm.setField("employee", value)} options={employeeOptions} required />
            <TextField label="Attendance date" type="date" value={markForm.values.attendanceDate} onChange={(value) => markForm.setField("attendanceDate", value)} required />
            <SelectField label="Status" value={markForm.values.status} onChange={(value) => markForm.setField("status", value)} options={STATUS_OPTIONS} required />
            <button type="submit" disabled={action.busy || !employeeOptions.length}>Record attendance</button>
          </form>
        </Panel>
      ) : (
        <Panel title="Read-only access" description="Your role can review teacher attendance but cannot mark or approve it." />
      )}

      <Panel title="Attendance records">
        <form className="form form-filters" onSubmit={(event) => event.preventDefault()}>
          <SelectField label="Teacher" value={filterForm.values.employee} onChange={(value) => filterForm.setField("employee", value)} options={employeeOptions} />
          <TextField label="From" type="date" value={filterForm.values.dateFrom} onChange={(value) => filterForm.setField("dateFrom", value)} />
          <TextField label="To" type="date" value={filterForm.values.dateTo} onChange={(value) => filterForm.setField("dateTo", value)} />
          <SelectField label="Status" value={filterForm.values.status} onChange={(value) => filterForm.setField("status", value)} options={STATUS_OPTIONS} />
        </form>
        {records.loading ? <LoadingState /> : null}
        <DataTable
          rows={records.data}
          columns={[
            { key: "date", label: "Date", render: (row) => text(row.attendance_date) },
            { key: "employee", label: "Teacher", render: (row) => employeeName(row.employee) },
            { key: "status", label: "Status", render: (row) => <StatusBadge value={row.status} /> },
            { key: "approval", label: "Approval", render: (row) => <StatusBadge value={row.approval_status} /> },
            {
              key: "actions",
              label: "Actions",
              render: (row) =>
                canApprove && row.approval_status === "draft" ? (
                  <button type="button" className="small-button" disabled={action.busy} onClick={() => approve(row.id)}>
                    Approve
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
