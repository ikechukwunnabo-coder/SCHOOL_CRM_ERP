import { expect, test } from "@playwright/test";
import { goToWorkflow, login, panel } from "./fixtures.js";

test("M3 workflows create calendar, timetable, and attendance records", async ({ page }) => {
  const state = await login(page);

  await goToWorkflow(page, "Academic calendar");
  const sessionPanel = panel(page, "New academic session");
  await sessionPanel.getByLabel("Name").fill("2027/2028");
  await sessionPanel.getByLabel("Code").fill("2027");
  await sessionPanel.getByLabel("Start date").fill("2027-09-01");
  await sessionPanel.getByLabel("End date").fill("2028-06-30");
  await sessionPanel.getByRole("button", { name: "Create session" }).click();
  await expect(page.getByText("Academic session created.")).toBeVisible();
  await expect(panel(page, "Academic sessions").getByText("2027/2028")).toBeVisible();

  await goToWorkflow(page, "Timetable");
  const timetablePanel = panel(page, "New timetable");
  await timetablePanel.getByLabel("Name").fill("Grade 10 draft");
  await timetablePanel.getByLabel("Academic session").selectOption("session-1");
  await timetablePanel.getByLabel("Class level").selectOption("class-1");
  await timetablePanel.getByRole("button", { name: "Create timetable" }).click();
  await expect(page.getByText("Timetable created.")).toBeVisible();

  const slotPanel = panel(page, "Add timetable slot");
  await slotPanel.getByLabel("Timetable").selectOption("timetable-1");
  await slotPanel.getByLabel("Subject offering").selectOption("offering-1");
  await slotPanel.getByLabel("Teacher").selectOption("employee-1");
  await slotPanel.getByLabel("Room").fill("R2");
  await slotPanel.getByRole("button", { name: "Add slot" }).click();
  await expect(page.getByText("Slot added to timetable.")).toBeVisible();

  await goToWorkflow(page, "Student attendance");
  const openPanel = panel(page, "Open attendance session");
  await openPanel.getByLabel("Subject offering").selectOption("offering-1");
  await openPanel.getByLabel("Attendance date").fill("2026-11-21");
  await openPanel.getByRole("button", { name: "Open session" }).click();
  await expect(page.getByText("Attendance session opened.")).toBeVisible();

  const markPanel = panel(page, "Mark attendance");
  await markPanel.getByLabel("Attendance session").selectOption("attendance-1");
  await expect(markPanel.getByLabel("Student").locator("option[value='student-1']")).toHaveCount(1);
  await markPanel.getByLabel("Student").selectOption("student-1");
  await markPanel.getByRole("button", { name: "Record attendance" }).click();
  await expect(page.getByText("Attendance recorded.")).toBeVisible();

  await goToWorkflow(page, "Teacher attendance");
  const teacherMarkPanel = panel(page, "Mark teacher attendance");
  await teacherMarkPanel.getByLabel("Teacher").selectOption("employee-1");
  await teacherMarkPanel.getByLabel("Attendance date").fill("2026-11-21");
  await teacherMarkPanel.getByRole("button", { name: "Record attendance" }).click();
  await expect(page.getByText("Teacher attendance recorded.")).toBeVisible();

  const teacherRecords = panel(page, "Attendance records");
  await teacherRecords.getByRole("button", { name: "Approve" }).first().click();
  await expect(page.getByText("Attendance approved.")).toBeVisible();

  const posted = state.calls.filter((call) => call.method === "POST").map((call) => call.path);
  expect(posted).toEqual(expect.arrayContaining([
    "/academic-sessions/",
    "/timetables/",
    "/timetables/timetable-1/add-slot/",
    "/attendance-sessions/open/",
    "/attendance-sessions/attendance-1/mark/",
    "/teacher-attendance/mark/",
    "/teacher-attendance/teacher-record-1/approve/",
  ]));
});
