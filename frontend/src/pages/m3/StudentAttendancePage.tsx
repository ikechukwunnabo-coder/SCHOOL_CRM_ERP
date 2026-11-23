import { useAuth } from "../../auth/AuthContext";
import { can } from "../../auth/permissions";
import { apiPost, optionLabel, shortDate, text, type Entity } from "../../api/resources";
import { DataTable } from "../../components/DataTable";
import { ErrorBanner, LoadingState, Notice, PageHeading, StatusBadge } from "../../components/Feedback";
import { SelectField, TextAreaField, TextField } from "../../components/FormControls";
import { Panel } from "../../components/Panel";
import { useAction } from "../../hooks/useAction";
import { useApiList, useApiResource } from "../../hooks/useApiResource";
import { useForm } from "../../hooks/useForm";

const STATUS_OPTIONS = [
  { value: "present", label: "Present" },
  { value: "absent", label: "Absent" },
  { value: "late", label: "Late" },
  { value: "excused", label: "Excused" },
];

export function StudentAttendancePage() {
  const { user } = useAuth();
  const attendanceSessions = useApiList<Entity>("/attendance-sessions/");
  const records = useApiList<Entity>("/attendance-records/");
  const offerings = useApiList<Entity>("/subject-offerings/");
  const subjects = useApiList<Entity>("/subjects/");
  const students = useApiList<Entity>("/students/");
  const action = useAction();
  const canCreate = can(user, "attendance", "create");
  const canUpdate = can(user, "attendance", "update");
  const openForm = useForm({ offering: "", attendanceDate: "" });
  const markForm = useForm({ attendance: "", student: "", status: "present" });
  const correctionForm = useForm({ record: "", newStatus: "present", reason: "" });
  const expected = useApiResource<Entity[]>(
    markForm.values.attendance ? `/attendance-sessions/${markForm.values.attendance}/expected-students/` : null,
  );

  const offeringOptions = offerings.data.map((item) => {
    const subject = subjects.data.find((entry) => entry.id === item.subject);
    return { value: item.id, label: subject ? optionLabel(subject) : text(item.id) };
  });
  const sessionOptions = attendanceSessions.data.map((item) => ({
    value: item.id,
    label: `${shortDate(item.attendance_date)} / ${offeringOptions.find((option) => option.value === item.offering)?.label || text(item.offering)}`,
  }));
  const studentName = (id: unknown) => {
    const match = students.data.find((item) => item.id === id);
    return match ? text(match.admission_number, text(match.first_name, text(id))) : text(id);
  };
  const recordOptions = records.data.map((item) => ({
    value: item.id,
    label: `${studentName(item.student)} / ${text(item.status)}`,
  }));
  const visibleRecords = markForm.values.attendance
    ? records.data.filter((record) => record.attendance_session === markForm.values.attendance)
    : records.data;

  const openSession = (event: React.FormEvent) => {
    event.preventDefault();
    void action.run(
      () =>
        apiPost<Entity>("/attendance-sessions/open/", {
          offering: openForm.values.offering,
          attendance_date: openForm.values.attendanceDate,
        }),
      () => {
        attendanceSessions.reload();
        openForm.reset();
        return "Attendance session opened.";
      },
    );
  };

  const mark = (event: React.FormEvent) => {
    event.preventDefault();
    void action.run(
      () =>
        apiPost<Entity>(`/attendance-sessions/${markForm.values.attendance}/mark/`, {
          student: markForm.values.student,
          status: markForm.values.status,
        }),
      () => {
        records.reload();
        return "Attendance recorded.";
      },
    );
  };

  const closeSession = (id: string) => {
    void action.run(
      () => apiPost<Entity>(`/attendance-sessions/${id}/close/`),
      () => {
        attendanceSessions.reload();
        return "Attendance session closed.";
      },
    );
  };

  const correct = (event: React.FormEvent) => {
    event.preventDefault();
    void action.run(
      () =>
        apiPost<Entity>(`/attendance-records/${correctionForm.values.record}/correct/`, {
          new_status: correctionForm.values.newStatus,
          reason: correctionForm.values.reason,
        }),
      () => {
        correctionForm.reset();
        records.reload();
        return "Correction submitted.";
      },
    );
  };

  return (
    <div className="page-stack">
      <PageHeading title="Student attendance" description="Open offering-based sessions, mark students, close the register, and request corrections." />
      <ErrorBanner message={action.error || attendanceSessions.error || records.error || offerings.error || expected.error} />
      <Notice message={action.notice} />

      {canCreate ? (
        <div className="grid">
          <Panel title="Open attendance session" description="One session per offering and date.">
            <form className="form" onSubmit={openSession}>
              <SelectField label="Subject offering" value={openForm.values.offering} onChange={(value) => openForm.setField("offering", value)} options={offeringOptions} required />
              <TextField label="Attendance date" type="date" value={openForm.values.attendanceDate} onChange={(value) => openForm.setField("attendanceDate", value)} required />
              <button type="submit" disabled={action.busy}>Open session</button>
            </form>
          </Panel>
          <Panel title="Mark attendance" description="Expected students are resolved from active class enrolments.">
            <form className="form" onSubmit={mark}>
              <SelectField label="Attendance session" value={markForm.values.attendance} onChange={(value) => markForm.setField("attendance", value)} options={sessionOptions} required />
              <SelectField label="Student" value={markForm.values.student} onChange={(value) => markForm.setField("student", value)} options={(expected.data || []).map((item) => ({ value: item.id, label: text(item.name, text(item.admission_number, item.id)) }))} required />
              <SelectField label="Status" value={markForm.values.status} onChange={(value) => markForm.setField("status", value)} options={STATUS_OPTIONS} required />
              <button type="submit" disabled={action.busy || !markForm.values.attendance}>Record attendance</button>
            </form>
          </Panel>
          {canUpdate ? (
            <Panel title="Correct a record" description="A reason is required and the correction is audited.">
              <form className="form" onSubmit={correct}>
                <SelectField label="Attendance record" value={correctionForm.values.record} onChange={(value) => correctionForm.setField("record", value)} options={recordOptions} required />
                <SelectField label="New status" value={correctionForm.values.newStatus} onChange={(value) => correctionForm.setField("newStatus", value)} options={STATUS_OPTIONS} required />
                <TextAreaField label="Reason" value={correctionForm.values.reason} onChange={(value) => correctionForm.setField("reason", value)} required />
                <button type="submit" disabled={action.busy}>Submit correction</button>
              </form>
            </Panel>
          ) : null}
        </div>
      ) : (
        <Panel title="Read-only access" description="Your role can review attendance but cannot open sessions or mark students." />
      )}

      <Panel title="Attendance sessions">
        {attendanceSessions.loading ? <LoadingState /> : null}
        <DataTable
          rows={attendanceSessions.data}
          columns={[
            { key: "date", label: "Date", render: (row) => shortDate(row.attendance_date) },
            { key: "offering", label: "Offering", render: (row) => offeringOptions.find((option) => option.value === row.offering)?.label || text(row.offering) },
            { key: "status", label: "Status", render: (row) => <StatusBadge value={row.status} /> },
            {
              key: "actions",
              label: "Actions",
              render: (row) =>
                canUpdate && row.status === "open" ? (
                  <button type="button" className="small-button" disabled={action.busy} onClick={() => closeSession(row.id)}>
                    Close register
                  </button>
                ) : (
                  <span className="muted">-</span>
                ),
            },
          ]}
        />
      </Panel>

      <Panel title="Attendance records">
        {records.loading ? <LoadingState /> : null}
        <DataTable
          rows={visibleRecords}
          empty="No records have been marked for this session."
          columns={[
            { key: "date", label: "Date", render: (row) => shortDate(attendanceSessions.data.find((item) => item.id === row.attendance_session)?.attendance_date) },
            { key: "student", label: "Student", render: (row) => studentName(row.student) },
            { key: "status", label: "Status", render: (row) => <StatusBadge value={row.status} /> },
            { key: "corrections", label: "Corrections", render: (row) => text(row.correction_count, "0") },
          ]}
        />
      </Panel>
    </div>
  );
}
