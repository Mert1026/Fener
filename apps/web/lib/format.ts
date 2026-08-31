import Decimal from "decimal.js";

export function money(value: string | null | undefined): string {
  if (value == null) return "Unknown";
  const decimal = new Decimal(value);
  if (decimal.isZero()) return "$0";
  const rounded = decimal.toDecimalPlaces(decimal.abs().lessThan(0.01) ? 8 : 4);
  return `$${rounded.isZero() ? decimal.toSignificantDigits(3).toString() : rounded.toString()}`;
}
export function tokens(value: number | null | undefined): string {
  if (value == null) return "Unknown";
  if (value >= 1_000_000) return `${Number((value / 1_000_000).toFixed(2))}M`;
  if (value >= 1000) return `${Number((value / 1000).toFixed(1))}K`;
  return value.toLocaleString();
}
export function date(value: string | null | undefined): string {
  if (!value) return "Not observed";
  const parsed = new Date(value);
  return Number.isNaN(parsed.valueOf())
    ? value
    : parsed.toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
      });
}
export function humanize(value: string): string {
  return value.replaceAll("_", " ").replaceAll("price.", "");
}
export function factValue(value: unknown): string {
  if (value == null) return "Unknown";
  if (typeof value === "boolean") return value ? "Supported" : "Not supported";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
