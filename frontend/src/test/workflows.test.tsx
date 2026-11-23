import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ADMIN_USER, EXAM_OFFICER_USER, RESULT, jsonResponse, paginated, renderApp } from "./fixtures";

describe("workflows", () => {
  it("records an academic session through the M3 calendar form", async () => {
    const user = userEvent.setup();
    const { fetchMock } = renderApp({ route: "/academics/calendar", user: ADMIN_USER });
    const heading = await screen.findByRole("heading", { name: "Academic calendar" });
    expect(heading).toBeInTheDocument();
    const panel = await screen.findByRole("heading", { name: "New academic session" }).then((element) => element.closest("section"));
    if (!panel) throw new Error("Session form panel not found");

    await user.type(within(panel).getByLabelText("Name"), "2027/2028");
    await user.type(within(panel).getByLabelText("Code"), "2027");
    fireEvent.change(within(panel).getByLabelText("Start date"), { target: { value: "2027-09-01" } });
    fireEvent.change(within(panel).getByLabelText("End date"), { target: { value: "2028-06-30" } });
    await user.click(within(panel).getByRole("button", { name: "Create session" }));

    expect(await screen.findByText("Academic session created.")).toBeInTheDocument();
    const call = fetchMock.mock.calls.find(([url, options]) => String(url).includes("/academic-sessions/") && options?.method === "POST");
    expect(call).toBeDefined();
    expect(JSON.parse(String(call?.[1]?.body))).toMatchObject({ name: "2027/2028", code: "2027" });
  });

  it("approves and publishes a submitted result in the M4 workflow", async () => {
    const user = userEvent.setup();
    let status = "submitted";
    const { fetchMock } = renderApp({
      route: "/examinations/results",
      user: EXAM_OFFICER_USER,
      responses: {
        "/examinations/results/": () => paginated([{ ...RESULT, status }]),
        "POST /examinations/results/result-1/approve/": () => {
          status = "approved";
          return { ...RESULT, status };
        },
        "POST /examinations/results/result-1/publish/": () => {
          status = "published";
          return { ...RESULT, status };
        },
      },
    });

    await user.click(await screen.findByRole("button", { name: "Approve" }));
    expect(await screen.findByText("Result approved.")).toBeInTheDocument();
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/examinations/results/result-1/approve/"), expect.objectContaining({ method: "POST" })));

    await user.click(await screen.findByRole("button", { name: "Publish" }));
    expect(await screen.findByText("Result published.")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/examinations/results/result-1/publish/"), expect.objectContaining({ method: "POST" }));
  });

  it("shows a clear API error when publishing is rejected", async () => {
    const user = userEvent.setup();
    renderApp({
      route: "/examinations/results",
      user: EXAM_OFFICER_USER,
      responses: {
        "/examinations/results/": paginated([{ ...RESULT, status: "approved" }]),
        "POST /examinations/results/result-1/publish/": () => jsonResponse({ errors: { detail: "Only approved results can be published." } }, 409),
      },
    });

    await user.click(await screen.findByRole("button", { name: "Publish" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Only approved results can be published.");
  });
});
