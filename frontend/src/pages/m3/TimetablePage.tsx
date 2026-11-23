import { useAuth } from "../../auth/AuthContext";
import { can } from "../../auth/permissions";
import { apiPost, numberValue, optionLabel, shortDate, text, type Entity } from "../../api/resources";
import { DataTable } from "../../components/DataTable";
import { ErrorBanner, LoadingState, Notice, PageHeading, StatusBadge } from "../../components/Feedback";
import { SelectField, TextField } from "../../components/FormControls";
import { Panel } from "../../components/Panel";
import { useAction } from "../../hooks/useAction";
import { useApiList } from "../../hooks/useApiResource";
import { useForm } from "../../hooks/useForm";

const DAY_OPTIONS = [
  { value: "1", label: "Monday" },
  { value: "2", label: "Tuesday" },
  { value: "3", label: "Wednesday" },
  { value: "4", label: "Thursday" },
  { value: "5", label: "Friday" },
];

const PERIOD_OPTIONS = Array.from({ length: 8 }, (_, index) => ({
  value: String(index + 1),
  label: `Period ${index + 1}`,
}));

export function TimetablePage() {
  const { user } = useAuth();
  const timetables = useApiList<Entity>("/timetables/");
  const slots = useApiList<Entity>("/timetable-slots/");
  const sessions = useApiList<Entity>("/academic-sessions/");
  const classLevels = useApiList<Entity>("/class-levels/");
  const offerings = useApiList<Entity>("/subject-offerings/");
  const employees = useApiList<Entity>("/employees/");
  const subjects = useApiList<Entity>("/subjects/");
  const action = useAction();
  const canCreate = can(user, "teaching", "create");
  const canApprove = can(user, "teaching", "approve");
  const canPublish = can(user, "teaching", "publish");
  const timetableForm = useForm({ name: "", session: "", classLevel: "" });
  const slotForm = useForm({
    timetable: "",
    dayOfWeek: "1",
    period: "1",
    offering: "",
    employee: "",
    room: "",
    recurrenceUntil: "",
  });

  const timetableOptions = timetables.data.map((item) => ({ value: item.id, label: text(item.name, `Version ${text(item.version)}`) }));
  const offeringOptions = offerings.data.map((item) => {
    const subject = subjects.data.find((entry) => entry.id === item.subject);
    return { value: item.id, label: subject ? optionLabel(subject) : text(item.id) };
  });
  const employeeOptions = employees.data.map((item) => ({
    value: item.id,
    label: `${text(item.employee_number)} ${text(item.first_name, "")} ${text(item.last_name, "")}`.trim(),
  }));
  const lookup = (rows: Entity[], id: unknown, fallback: string) => {
    const match = rows.find((row) => row.id === id);
    return match ? text(match.name, text(match.code, fallback)) : fallback;
  };
  const visibleSlots = slotForm.values.timetable
    ? slots.data.filter((slot) => slot.timetable === slotForm.values.timetable)
    : slots.data;

  const createTimetable = (event: React.FormEvent) => {
    event.preventDefault();
    void action.run(
      () =>
        apiPost<Entity>("/timetables/", {
          name: timetableForm.values.name,
          session: timetableForm.values.session,
          class_level: timetableForm.values.classLevel,
        }),
      () => {
        timetableForm.reset();
        timetables.reload();
        return "Timetable created.";
      },
    );
  };

  const addSlot = (event: React.FormEvent) => {
    event.preventDefault();
    const values = slotForm.values;
    void action.run(
      () =>
        apiPost<Entity>(`/timetables/${values.timetable}/add-slot/`, {
          day_of_week: numberValue(values.dayOfWeek),
          period: numberValue(values.period),
          offering: values.offering,
          employee: values.employee,
          room: values.room,
          recurrence: "weekly",
          recurrence_until: values.recurrenceUntil || undefined,
        }),
      () => {
        slots.reload();
        return "Slot added to timetable.";
      },
    );
  };

  const runAction = (id: string, path: string, message: string) => {
    void action.run(
      () => apiPost<Entity>(`/timetables/${id}/${path}/`),
      () => {
        timetables.reload();
        slots.reload();
        return message;
      },
    );
  };

  return (
    <div className="page-stack">
      <PageHeading title="Timetable" description="Build draft timetables, add slots, then approve and publish them." />
      <ErrorBanner message={action.error || timetables.error || slots.error || offerings.error || employees.error} />
      <Notice message={action.notice} />

      {canCreate ? (
        <div className="grid">
          <Panel title="New timetable" description="Start a draft for a session and class level.">
            <form className="form" onSubmit={createTimetable}>
              <TextField label="Name" value={timetableForm.values.name} onChange={(value) => timetableForm.setField("name", value)} required />
              <SelectField label="Academic session" value={timetableForm.values.session} onChange={(value) => timetableForm.setField("session", value)} options={sessions.data.map((item) => ({ value: item.id, label: optionLabel(item) }))} required />
              <SelectField label="Class level" value={timetableForm.values.classLevel} onChange={(value) => timetableForm.setField("classLevel", value)} options={classLevels.data.map((item) => ({ value: item.id, label: optionLabel(item) }))} required />
              <button type="submit" disabled={action.busy}>Create timetable</button>
            </form>
          </Panel>
          <Panel title="Add timetable slot" description="Conflicts are checked by the server for teacher, class, and room.">
            <form className="form" onSubmit={addSlot}>
              <SelectField label="Timetable" value={slotForm.values.timetable} onChange={(value) => slotForm.setField("timetable", value)} options={timetableOptions} required />
              <div className="form-row">
                <SelectField label="Day" value={slotForm.values.dayOfWeek} onChange={(value) => slotForm.setField("dayOfWeek", value)} options={DAY_OPTIONS} required />
                <SelectField label="Period" value={slotForm.values.period} onChange={(value) => slotForm.setField("period", value)} options={PERIOD_OPTIONS} required />
              </div>
              <SelectField label="Subject offering" value={slotForm.values.offering} onChange={(value) => slotForm.setField("offering", value)} options={offeringOptions} required />
              <SelectField label="Teacher" value={slotForm.values.employee} onChange={(value) => slotForm.setField("employee", value)} options={employeeOptions} required />
              <TextField label="Room" value={slotForm.values.room} onChange={(value) => slotForm.setField("room", value)} required />
              <TextField label="Repeat until" type="date" value={slotForm.values.recurrenceUntil} onChange={(value) => slotForm.setField("recurrenceUntil", value)} />
              <button type="submit" disabled={action.busy || !timetableOptions.length}>Add slot</button>
            </form>
          </Panel>
        </div>
      ) : (
        <Panel title="Read-only access" description="Your role can view timetables but cannot change them." />
      )}

      <Panel title="Timetables">
        {timetables.loading ? <LoadingState /> : null}
        <DataTable
          rows={timetables.data}
          columns={[
            { key: "name", label: "Timetable", render: (row) => text(row.name) },
            { key: "session", label: "Session", render: (row) => lookup(sessions.data, row.session, text(row.session)) },
            { key: "class", label: "Class level", render: (row) => lookup(classLevels.data, row.class_level, text(row.class_level)) },
            { key: "version", label: "Version", render: (row) => text(row.version) },
            { key: "status", label: "Status", render: (row) => <StatusBadge value={row.status} /> },
            {
              key: "actions",
              label: "Actions",
              render: (row) => (
                <div className="row-actions">
                  {canApprove && !row.approved_at ? (
                    <button type="button" className="small-button" disabled={action.busy} onClick={() => runAction(row.id, "approve", "Timetable approved.")}>
                      Approve
                    </button>
                  ) : null}
                  {canPublish && row.approved_at && row.status !== "published" ? (
                    <button type="button" className="small-button" disabled={action.busy} onClick={() => runAction(row.id, "publish", "Timetable published.")}>
                      Publish
                    </button>
                  ) : null}
                  {canCreate && row.status === "published" ? (
                    <button type="button" className="small-button secondary" disabled={action.busy} onClick={() => runAction(row.id, "revise", "Draft revision created.")}>
                      Revise
                    </button>
                  ) : null}
                </div>
              ),
            },
          ]}
        />
      </Panel>

      <Panel title="Timetable slots" description={slotForm.values.timetable ? undefined : "Select a timetable in the slot form to narrow this list."}>
        {slots.loading ? <LoadingState /> : null}
        <DataTable
          rows={visibleSlots}
          empty="No slots for this timetable."
          columns={[
            { key: "day", label: "Day", render: (row) => text(DAY_OPTIONS.find((option) => option.value === String(row.day_of_week))?.label, text(row.day_of_week)) },
            { key: "period", label: "Period", render: (row) => text(row.period) },
            { key: "offering", label: "Subject offering", render: (row) => offeringOptions.find((option) => option.value === row.offering)?.label || text(row.offering) },
            { key: "employee", label: "Teacher", render: (row) => employeeOptions.find((option) => option.value === row.employee)?.label || text(row.employee) },
            { key: "room", label: "Room", render: (row) => text(row.room) },
            { key: "recurrence", label: "Recurrence", render: (row) => `${text(row.recurrence)} x${text(row.recurrence_interval, "1")}` },
            { key: "until", label: "Until", render: (row) => shortDate(row.recurrence_until) },
          ]}
        />
      </Panel>
    </div>
  );
}
