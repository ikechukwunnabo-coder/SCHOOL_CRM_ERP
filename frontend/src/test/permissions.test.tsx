import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ADMIN_USER, EXAM_OFFICER_USER, REGISTRAR_USER, TEACHER_USER, renderApp } from "./fixtures";

describe("permission-based actions", () => {
  it("shows report card generation to an administrator", async () => {
    renderApp({ route: "/examinations/report-cards", user: ADMIN_USER });
    expect(await screen.findByRole("button", { name: "Generate report card" })).toBeInTheDocument();
  });

  it("hides report card generation from a registrar", async () => {
    renderApp({ route: "/examinations/report-cards", user: REGISTRAR_USER });
    expect(await screen.findByRole("heading", { name: "Report cards" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Generate report card" })).not.toBeInTheDocument();
  });

  it("shows result approval to an examination officer", async () => {
    renderApp({ route: "/examinations/results", user: EXAM_OFFICER_USER });
    expect(await screen.findByRole("button", { name: "Approve" })).toBeInTheDocument();
  });

  it("hides result approval from a subject teacher", async () => {
    renderApp({ route: "/examinations/results", user: TEACHER_USER });
    expect(await screen.findByRole("heading", { name: "Results workflow" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
  });
});
