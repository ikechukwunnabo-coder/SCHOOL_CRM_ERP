import { expect, test } from "@playwright/test";
import { goToWorkflow, login, panel } from "./fixtures.js";

test("M4 workflows publish results, download a report card, and verify a transcript", async ({ page }) => {
  const state = await login(page);

  await goToWorkflow(page, "Results workflow");
  const resultRow = page.getByRole("row").filter({ hasText: "STU-1 Grace Hopper" });
  await expect(resultRow).toBeVisible();
  await resultRow.getByRole("button", { name: "Approve" }).click();
  await expect(page.getByText("Result approved.")).toBeVisible();
  await expect(resultRow.getByRole("button", { name: "Publish" })).toBeVisible();
  await resultRow.getByRole("button", { name: "Publish" }).click();
  await expect(page.getByText("Result published.")).toBeVisible();

  await goToWorkflow(page, "Report cards");
  const generatePanel = panel(page, "Generate report card");
  await generatePanel.getByLabel("Student").selectOption("student-1");
  await generatePanel.getByLabel("Academic session").selectOption("session-1");
  await generatePanel.getByLabel("Term").selectOption("term-1");
  await generatePanel.getByRole("button", { name: "Generate report card" }).click();
  await expect(page.getByText("Report card generated.")).toBeVisible();

  const cardRow = page.getByRole("row").filter({ hasText: "RC-2026-1" });
  const cardDownload = page.waitForEvent("download");
  await cardRow.getByRole("button", { name: "Download PDF" }).click();
  expect((await cardDownload).suggestedFilename()).toBe("RC-2026-1.pdf");

  await goToWorkflow(page, "Transcripts");
  const requestPanel = panel(page, "Request transcript");
  await requestPanel.getByLabel("Student").selectOption("student-1");
  await requestPanel.getByLabel("Purpose").fill("Visa application");
  await requestPanel.getByRole("button", { name: "Submit request" }).click();
  await expect(page.getByText("Transcript request submitted.")).toBeVisible();

  const decisionsPanel = panel(page, "Request decisions");
  await decisionsPanel.getByLabel("Request").selectOption("request-1");
  await decisionsPanel.getByRole("button", { name: "Generate transcript" }).click();
  await expect(page.getByText("Request generate completed.")).toBeVisible();
  await expect(page.getByText("verify-token-123")).toBeVisible();

  const verifyPanel = panel(page, "Verify a transcript");
  await verifyPanel.getByLabel("Verification token").fill("verify-token-123");
  await verifyPanel.getByRole("button", { name: "Verify token" }).click();
  await expect(page.getByText("Token is valid.")).toBeVisible();
  await expect(verifyPanel.getByText("TR-2026-1")).toBeVisible();

  const issuePanel = panel(page, "Issue transcript");
  await issuePanel.getByLabel("Transcript").selectOption("transcript-1");
  await issuePanel.getByLabel("Issued to").fill("Grace Hopper");
  await issuePanel.getByRole("button", { name: "Issue transcript" }).click();
  await expect(page.getByText("Transcript issued.")).toBeVisible();

  const transcriptRow = panel(page, "Transcripts").getByRole("row").filter({ hasText: "TR-2026-1" });
  await expect(transcriptRow.getByRole("button", { name: "Download PDF" })).toBeVisible();
  const transcriptDownload = page.waitForEvent("download");
  await transcriptRow.getByRole("button", { name: "Download PDF" }).click();
  expect((await transcriptDownload).suggestedFilename()).toBe("TR-2026-1.pdf");

  const posted = state.calls.filter((call) => call.method === "POST").map((call) => call.path);
  expect(posted).toEqual(expect.arrayContaining([
    "/examinations/results/result-1/approve/",
    "/examinations/results/result-1/publish/",
    "/examinations/report-cards/generate/",
    "/transcripts/requests/",
    "/transcripts/requests/request-1/generate/",
    "/transcripts/verify/",
    "/transcripts/transcript-1/issue/",
  ]));
  expect(state.calls).toEqual(expect.arrayContaining([
    expect.objectContaining({ method: "GET", path: "/examinations/report-cards/card-1/download/" }),
    expect.objectContaining({ method: "GET", path: "/transcripts/transcript-1/download/" }),
  ]));
});
