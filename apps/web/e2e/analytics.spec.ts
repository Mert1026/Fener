import { expect, test } from "@playwright/test";
import type { ModelPage } from "../lib/api";

test("wide tables keep their overflow inside the scroll region on tablets", async ({
  page,
}) => {
  await page.setViewportSize({ width: 768, height: 1000 });
  await page.goto("/");
  await expect(page.locator(".responsive-table")).toBeVisible();
  await expect
    .poll(() => page.evaluate(() => document.documentElement.scrollWidth))
    .toBe(768);
});

test("catalog analysis stays scoped and its breakdown is keyboard operable", async ({
  page,
}) => {
  await page.goto("/models?include_unresolved=true");
  await expect(
    page.getByRole("checkbox", { name: "Include unresolved identities" }),
  ).toBeChecked();
  const analysis = page.getByRole("region", { name: "Catalog analysis" });
  await expect(analysis).toBeVisible();
  const capability = analysis.getByRole("button", {
    name: "Capabilities",
    exact: true,
  });
  await capability.focus();
  await page.keyboard.press("Enter");
  await expect(capability).toHaveAttribute("aria-pressed", "true");
  await expect(analysis.getByText(/missing support is unknown/)).toBeVisible();
});

test("context chart provides zoom controls and accessible model links", async ({
  page,
}) => {
  await page.goto("/");
  const chart = page.getByRole("group", { name: "Context and cost explorer" });
  await expect(chart.locator("canvas")).toBeVisible();
  await chart
    .getByRole("button", { name: "Zoom in on context and cost" })
    .click();
  await expect(chart.getByRole("status")).toContainText("2.0×");
  await chart
    .getByRole("button", { name: "Reset context and cost zoom" })
    .click();
  await expect(chart.getByRole("status")).toHaveText("Full range");
  await chart.locator("summary").click();
  await expect(chart.getByRole("table")).toBeVisible();
  await expect(chart.getByRole("link").first()).toHaveAttribute(
    "href",
    /\/models\//,
  );
});

test("price evidence supports series selection and an exact-value table", async ({
  page,
  request,
}) => {
  const result = await request.get(
    "/api/backend/models?limit=100&sort=released",
  );
  expect(result.ok()).toBe(true);
  const catalog = (await result.json()) as ModelPage;
  const model = catalog.items.find(
    (item) => item.deployment_count > 0 && item.input_price_from !== null,
  );
  test.skip(!model, "Requires a real model with observed serving prices");
  await page.goto(`/models/${model!.id}`);
  await page.getByRole("tab", { name: "Price history", exact: true }).click();
  const series = page.locator(".chart-legend-item").first();
  await expect(series).toHaveAttribute("aria-pressed", "true");
  await series.click();
  await expect(series).toHaveAttribute("aria-pressed", "false");
  await series.click();
  await expect(series).toHaveAttribute("aria-pressed", "true");
  await page.getByText("Read the price observations", { exact: true }).click();
  await expect(
    page.getByRole("columnheader", { name: "USD / 1M tokens", exact: true }),
  ).toBeVisible();
});
