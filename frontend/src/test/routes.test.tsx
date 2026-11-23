import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ADMIN_USER, TEACHER_USER, renderApp } from "./fixtures";

const ROUTES = [
  ["/academics/calendar", "Academic calendar"],
  ["/academics/timetable", "Timetable"],
  ["/teaching/workload", "Teacher workload"],
  ["/attendance/students", "Student attendance"],
  ["/attendance/teachers", "Teacher attendance"],
  ["/examinations/results", "Results workflow"],
  ["/examinations/report-cards", "Report cards"],
  ["/transcripts", "Transcripts"],
] as const;

describe("authenticated routes", () => {
  it("redirects anonymous visitors to login", async () => {
    renderApp({ route: "/examinations/results", user: null });
    expect(await screen.findByRole("heading", { name: "School CRM & ERP" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Results workflow" })).not.toBeInTheDocument();
  });

  it.each(ROUTES)("renders %s for an authorized user", async (route, heading) => {
    renderApp({ route, user: ADMIN_USER });
    expect(await screen.findByRole("heading", { name: heading, level: 2 })).toBeInTheDocument();
  });

  it("blocks a module the user role cannot view", async () => {
    renderApp({ route: "/transcripts", user: TEACHER_USER });
    expect(await screen.findByRole("heading", { name: "Not available" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Transcripts" })).not.toBeInTheDocument();
  });
});
