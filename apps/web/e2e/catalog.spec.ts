import { expect, test } from "@playwright/test";
import type { ModelPage } from "../lib/api";

test("real catalog search, selection, comparison and cost calculation", async ({
  page,
  request,
}) => {
  const response = await request.get(
    "/api/backend/models?limit=100&sort=released",
  );
  expect(
    response.ok(),
    "Start the API and web server before this acceptance suite",
  ).toBe(true);
  const catalog = (await response.json()) as ModelPage;
  const candidates = catalog.items
    .filter((model) => model.deployment_count > 0)
    .slice(0, 2);
  test.skip(
    candidates.length < 2,
    "Two models with serving deployments are required; this suite never seeds production data",
  );
  await page.goto("/models");
  for (const model of candidates) {
    await page
      .getByRole("textbox", { name: "Search models", exact: true })
      .fill(model.name);
    // A previous result can already contain the next model. Wait for the
    // debounced filter to commit before selecting and navigating away.
    await expect
      .poll(() => new URL(page.url()).searchParams.get("q"))
      .toBe(model.name);
    const row = page
      .getByRole("row")
      .filter({ has: page.locator(`a[href="/models/${model.id}"]`) });
    await row.getByRole("checkbox").check();
  }
  await page.getByRole("link", { name: "Compare models", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Compare the trade-offs", exact: true }),
  ).toBeVisible();
  const results = page.waitForResponse(
    (r) => r.url().endsWith("/cost") && r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Calculate costs", exact: true })
    .click();
  expect((await results).ok()).toBe(true);
  await expect(
    page.getByRole("button", { name: "Calculate costs", exact: true }),
  ).toBeEnabled();
  await expect(
    page.getByText("Same-origin request required", { exact: true }),
  ).toHaveCount(0);
});

test("private pages fail closed and the mobile navigation works", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/research");
  await expect(
    page.getByText("This is your private intelligence.", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Toggle navigation", exact: true })
    .click();
  await page.getByRole("link", { name: "Models", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Model explorer", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Toggle color theme", exact: true })
    .click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
});
