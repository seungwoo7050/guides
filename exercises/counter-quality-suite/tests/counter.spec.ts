import { expect, test } from "@playwright/test";

// [Implementation 7] Verify the observable user flow through roles, names, and live status instead of coupling the browser test to DOM implementation details.
test("a user changes and resets the counter", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("status")).toHaveText("0");
  await page.getByRole("button", { name: "Increment" }).click();
  await expect(page.getByRole("status")).toHaveText("1");
  await page.getByRole("button", { name: "Decrement" }).click();
  await expect(page.getByRole("status")).toHaveText("0");
  await page.getByRole("button", { name: "Decrement" }).click();
  await expect(page.getByRole("status")).toHaveText("0");
  await page.getByRole("button", { name: "Increment" }).click();
  await page.getByRole("button", { name: "Reset" }).click();
  await expect(page.getByRole("status")).toHaveText("0");
});
