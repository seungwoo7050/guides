import { expect, test } from "@playwright/test";
// [Implementation 7] E2E는 CSS 내부 구조 대신 role·name과 관찰 가능한 status로 실제 사용자 흐름을 검증합니다.
test("user increments the counter", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("status")).toHaveText("0");
  await page.getByRole("button", { name: "증가" }).click();
  await expect(page.getByRole("status")).toHaveText("1");
  await page.getByRole("button", { name: "감소" }).click();
  await expect(page.getByRole("status")).toHaveText("0");
  await page.getByRole("button", { name: "감소" }).click();
  await expect(page.getByRole("status")).toHaveText("0");
});
