import { useAuth } from "../../auth/AuthContext";
import { CLASS_TEACHER, SUBJECT_TEACHER, can, hasAnyRole } from "../../auth/permissions";
import { apiPost, numberValue, optionLabel, shortDate, text, type Entity } from "../../api/resources";
import { DataTable } from "../../components/DataTable";
import { ErrorBanner, LoadingState, Notice, PageHeading, StatusBadge } from "../../components/Feedback";
import { SelectField, TextField } from "../../components/FormControls";
import { Panel } from "../../components/Panel";
import { useAction } from "../../hooks/useAction";
import { useApiList } from "../../hooks/useApiResource";
import { useForm } from "../../hooks/useForm";

export function TeacherWorkloadPage() {
  const { user } = useAuth();
  const assignments = useApiList<Entity>("/teacher-assignments/");
  const myAssignments = useApiList<Entity>(hasAnyRole(user, [CLASS_TEACHER, SUBJECT_TEACHER]) ? "/teacher-assignments/my-assignments/" : null);
  const policies = useApiList<Entity>("/workload-policies/");
  const employees = useApiList<Entity>("/employees/");
  const offerings = useApiList<Entity>("/subject-offerings/");
  const subjects = useApiList<Entity>("/subjects/");
  const action = useAction();
  const canManage = can(user, "teaching", "update");
  const canCreatePolicy = can(user, "teaching", "create");
  const isTeacher = hasAnyRole(user, [CLASS_TEACHER, SUBJECT_TEACHER]);
  const policyForm = useForm({ name: "Teacher workload", effectiveFrom: "", effectiveTo: "", maxHours: "", institution: user?.institution || "" });
  const reassignForm = useForm({ assignment: "", startDate: "", endDate: "", workloadHours: "" });

  const employeeLabel = (id: unknown) => {
    const match = employees.data.find((item) => item.id === id);
    return match ? `${text(match.employee_number)} ${text(match.first_name, "")} ${text(match.last_name, "")}`.trim() : text(id);
  };
  const offeringLabel = (id: unknown) => {
    const offering = offerings.data.find((item) => item.id === id);
    if (!offering) return text(id);
    const subject = subjects.data.find((item) => item.id === offering.subject);
    return subject ? optionLabel(subject) : text(offering.id);
  };
  const assignmentOptions = assignments.data.map((item) => ({
    value: item.id,
    label: employeeLabel(item.employee) + " / " + offeringLabel(item.offering),
  }));

  const createPolicy = (event: React.FormEvent) => {
    event.preventDefault();
    const values = policyForm.values;
    void action.run(
      () =>
        apiPost<Entity>("/workload-policies/", {
          name: values.name,
          institution: values.institution || user?.institution,
          effective_from: values.effectiveFrom,
          effective_to: values.effectiveTo || undefined,
          max_hours: numberValue(values.maxHours),
        }),
      () => {
        policies.reload();
        return "Workload policy created.";
      },
    );
  };

  const reassign = (event: React.FormEvent) => {
    event.preventDefault();
    const values = reassignForm.values;
    void action.run(
      () =>
        apiPost<Entity>(`/teacher-assignments/${values.assignment}/reassign/`, {
          start_date: values.startDate,
          end_date: values.endDate,
          workload_hours: numberValue(values.workloadHours),
        }),
      () => {
        assignments.reload();
        myAssignments.reload();
        return "Assignment updated.";
      },
    );
  };

  return (
    <div className="page-stack">
      <PageHeading title="Teacher workload" description="Review effective-dated assignments, reassign teaching load, and configure workload policies." />
      <ErrorBanner message={action.error || assignments.error || policies.error || myAssignments.error} />
      <Notice message={action.notice} />

      {canCreatePolicy || canManage ? (
        <div className="grid">
          {canCreatePolicy ? (
            <Panel title="New workload policy" description="Sets the maximum weekly teaching hours for a date range.">
              <form className="form" onSubmit={createPolicy}>
                <TextField label="Name" value={policyForm.values.name} onChange={(value) => policyForm.setField("name", value)} required />
                {user?.institution ? null : <TextField label="Institution ID" value={policyForm.values.institution} onChange={(value) => policyForm.setField("institution", value)} required />}
                <TextField label="Effective from" type="date" value={policyForm.values.effectiveFrom} onChange={(value) => policyForm.setField("effectiveFrom", value)} required />
                <TextField label="Effective to" type="date" value={policyForm.values.effectiveTo} onChange={(value) => policyForm.setField("effectiveTo", value)} />
                <TextField label="Maximum hours" type="number" min="1" value={policyForm.values.maxHours} onChange={(value) => policyForm.setField("maxHours", value)} required />
                <button type="submit" disabled={action.busy}>Create policy</button>
              </form>
            </Panel>
          ) : null}
          {canManage ? (
            <Panel title="Reassign teacher" description="Existing offering, teacher, and role are retained by the server.">
              <form className="form" onSubmit={reassign}>
                <SelectField label="Assignment" value={reassignForm.values.assignment} onChange={(value) => reassignForm.setField("assignment", value)} options={assignmentOptions} required />
                <div className="form-row">
                  <TextField label="Start date" type="date" value={reassignForm.values.startDate} onChange={(value) => reassignForm.setField("startDate", value)} required />
                  <TextField label="End date" type="date" value={reassignForm.values.endDate} onChange={(value) => reassignForm.setField("endDate", value)} required />
                </div>
                <TextField label="Workload hours" type="number" min="0" value={reassignForm.values.workloadHours} onChange={(value) => reassignForm.setField("workloadHours", value)} required />
                <button type="submit" disabled={action.busy || !assignmentOptions.length}>Update assignment</button>
              </form>
            </Panel>
          ) : null}
        </div>
      ) : (
        <Panel title="Read-only access" description="Your role can review workload information but cannot change it." />
      )}

      {isTeacher ? (
        <Panel title="My assignments" description="Assignments resolved for the signed-in teacher.">
          {myAssignments.loading ? <LoadingState /> : null}
          <DataTable
            rows={myAssignments.data}
            empty="No assignments are linked to your account."
            columns={[
              { key: "offering", label: "Subject offering", render: (row) => offeringLabel(row.offering) },
              { key: "role", label: "Role", render: (row) => text(row.role) },
              { key: "dates", label: "Dates", render: (row) => `${shortDate(row.start_date)} to ${shortDate(row.end_date)}` },
              { key: "hours", label: "Hours", render: (row) => text(row.workload_hours) },
              { key: "status", label: "Status", render: (row) => <StatusBadge value={row.status} /> },
            ]}
          />
        </Panel>
      ) : null}

      <Panel title="Teacher assignments">
        {assignments.loading ? <LoadingState /> : null}
        <DataTable
          rows={assignments.data}
          columns={[
            { key: "employee", label: "Teacher", render: (row) => employeeLabel(row.employee) },
            { key: "offering", label: "Subject offering", render: (row) => offeringLabel(row.offering) },
            { key: "role", label: "Role", render: (row) => text(row.role) },
            { key: "dates", label: "Dates", render: (row) => `${shortDate(row.start_date)} to ${shortDate(row.end_date)}` },
            { key: "hours", label: "Hours", render: (row) => text(row.workload_hours) },
            { key: "status", label: "Status", render: (row) => <StatusBadge value={row.status} /> },
          ]}
        />
      </Panel>

      <Panel title="Workload policies">
        {policies.loading ? <LoadingState /> : null}
        <DataTable
          rows={policies.data}
          columns={[
            { key: "name", label: "Policy", render: (row) => text(row.name) },
            { key: "max", label: "Max hours", render: (row) => text(row.max_hours) },
            { key: "dates", label: "Effective", render: (row) => `${shortDate(row.effective_from)} to ${shortDate(row.effective_to)}` },
          ]}
        />
      </Panel>
    </div>
  );
}
