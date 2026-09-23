import { expect, test } from "@playwright/test";

test.describe("Landing page", () => {
  test("renders the hero, navigation, and CTAs", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toContainText(/water/i);

    await expect(page.getByRole("link", { name: /start monitoring/i }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: /methodology/i }).first()).toBeVisible();

    await page.getByRole("link", { name: /start monitoring/i }).first().click();
    await expect(page).toHaveURL(/monitor/);
  });
});
