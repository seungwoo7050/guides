import { expect, test } from "@playwright/test";
test("user increments the counter", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("status")).toHaveText("0");
  await page.getByRole("button", { name: "증가" }).click();
  await expect(page.getByRole("status")).toHaveText("1");
});
