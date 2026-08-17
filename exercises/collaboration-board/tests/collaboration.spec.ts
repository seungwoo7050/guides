import { expect, test } from "@playwright/test";

// [Implementation 10] Verify one authenticated cross-layer workflow through the browser, HTTP API, WebSocket join, durable board mutation, and observable UI projection.
test("an owner creates a board and publishes a realtime note", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Handle").fill("owner");
  await page.getByLabel("Display name").fill("Board Owner");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Boards", exact: true })).toBeVisible();

  const title = `Roadmap ${Date.now()}`;
  await page.getByLabel("New board").fill(title);
  await page.getByRole("button", { name: "Create" }).click();
  const card = page.getByRole("article").filter({ hasText: title });
  await expect(card).toBeVisible();
  await card.getByRole("link", { name: "Open board" }).click();

  await expect(page.getByRole("status")).toContainText("connected");
  await page.getByLabel("New note").fill("Ship verified collaboration");
  await page.getByRole("button", { name: "Add" }).click();
  await expect(page.getByText("Ship verified collaboration")).toBeVisible();
});
