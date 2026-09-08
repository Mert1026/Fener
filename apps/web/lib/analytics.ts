import type { Model, Provider, Deployment, MarketEvent } from "./api";

export function catalogSummary(models: Model[]) {
  const priced = models.filter(
    (m) =>
      m.input_price_from !== null &&
      Number.isFinite(Number(m.input_price_from)) &&
      Number(m.input_price_from) >= 0,
  );
  const prices = priced
    .map((m) => Number(m.input_price_from))
    .sort((a, b) => a - b);
  const middle = Math.floor(prices.length / 2);
  return {
    total: models.length,
    priced: priced.length,
    median: prices.length
      ? prices.length % 2
        ? prices[middle]
        : (prices[middle - 1] + prices[middle]) / 2
      : null,
    context: [
      {
        label: "Under 32K",
        value: models.filter(
          (m) => m.context_window !== null && m.context_window < 32000,
        ).length,
      },
      {
        label: "32K–128K",
        value: models.filter(
          (m) =>
            m.context_window !== null &&
            m.context_window >= 32000 &&
            m.context_window < 128000,
        ).length,
      },
      {
        label: "128K–1M",
        value: models.filter(
          (m) =>
            m.context_window !== null &&
            m.context_window >= 128000 &&
            m.context_window < 1000000,
        ).length,
      },
      {
        label: "1M or more",
        value: models.filter(
          (m) => m.context_window !== null && m.context_window >= 1000000,
        ).length,
      },
      {
        label: "Unknown",
        value: models.filter((m) => m.context_window === null).length,
      },
    ],
    capabilities: [
      "tool_calling",
      "reasoning",
      "image_input",
      "structured_output",
    ].map((key) => ({
      label: {
        tool_calling: "Tool calling",
        reasoning: "Reasoning",
        image_input: "Vision",
        structured_output: "Structured output",
      }[key]!,
      value: models.filter((m) => m.capabilities.includes(key)).length,
    })),
  };
}

export function providerSummary(providers: Provider[]) {
  const active = providers.filter((p) => p.deployment_count > 0);
  const total = active.reduce((sum, p) => sum + p.deployment_count, 0);
  const leaders = [...active]
    .sort(
      (a, b) =>
        b.deployment_count - a.deployment_count || a.name.localeCompare(b.name),
    )
    .slice(0, 5);
  return { total, active: active.length, leaders };
}

export function deploymentCoverage(deployments: Deployment[]) {
  return [
    ["Input price", "price.input_tokens"],
    ["Output price", "price.output_tokens"],
    ["Context limit", "context_window"],
    ["Availability", "availability"],
  ].map(([label, key]) => ({
    label,
    value: deployments.filter((d) => d.facts[key]?.value != null).length,
  }));
}

export function eventComposition(events: MarketEvent[]) {
  const counts = new Map<string, number>();
  for (const event of events)
    counts.set(event.event_type, (counts.get(event.event_type) ?? 0) + 1);
  return [...counts]
    .sort((a, b) => b[1] - a[1])
    .map(([label, value]) => ({ label: label.replaceAll("_", " "), value }));
}
