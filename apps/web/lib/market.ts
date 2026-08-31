import Decimal from "decimal.js";
import type { MarketEvent } from "./api";
import { humanize } from "./format";

const ExactDecimal = Decimal.clone({ precision: 120 });

type Price = {
  amount: string | number;
  quantity: number;
  currency: string;
  unit: string;
};
function price(value: unknown): Price | null {
  if (!value || typeof value !== "object") return null;
  const row = value as Price;
  try {
    return typeof row.currency === "string" &&
      typeof row.unit === "string" &&
      new ExactDecimal(row.quantity).isFinite() &&
      new ExactDecimal(row.quantity).gt(0) &&
      new ExactDecimal(row.amount).isFinite()
      ? row
      : null;
  } catch {
    return null;
  }
}
function plain(value: unknown): string {
  if (value == null) return "Not reported";
  if (typeof value === "boolean") return value ? "Enabled" : "Disabled";
  if (typeof value === "number")
    return value.toLocaleString("en-US", { maximumFractionDigits: 12 });
  if (typeof value === "string") return humanize(value);
  if (Array.isArray(value)) return value.map(plain).join(", ");
  return "Details updated";
}
export function marketChange(event: MarketEvent) {
  const before = price(event.old_value),
    after = price(event.new_value);
  let oldLabel = plain(event.old_value),
    newLabel = plain(event.new_value),
    unit = "";
  let delta: Decimal | null = null;
  let direction: "up" | "down" | "flat" | "new" = "flat";
  const field = event.change_field ?? "";
  if (before && after) {
    // Normalize both sides to the same display quantity without float rounding.
    const basis = after.unit === "tokens" ? 1_000_000 : 1;
    const previous = new ExactDecimal(before.amount)
      .mul(basis)
      .div(before.quantity);
    const next = new ExactDecimal(after.amount).mul(basis).div(after.quantity);
    const label = (value: Decimal, currency: string) =>
      `${currency === "USD" ? "$" : `${currency} `}${value.toString()}`;
    oldLabel = label(previous, before.currency);
    newLabel = label(next, after.currency);
    unit = `per ${basis === 1_000_000 ? "1M" : "1"} ${humanize(after.unit)}`;
    if (before.currency === after.currency && before.unit === after.unit) {
      direction = next.eq(previous)
        ? "flat"
        : next.gt(previous)
          ? "up"
          : "down";
      if (previous.gt(0)) delta = next.minus(previous).div(previous).mul(100);
    } else {
      oldLabel = `${plain(before.amount)} ${before.currency} / ${before.quantity} ${before.unit}`;
      newLabel = `${plain(after.amount)} ${after.currency} / ${after.quantity} ${after.unit}`;
      unit = "Billing basis changed";
    }
  } else if (
    typeof event.old_value === "number" &&
    typeof event.new_value === "number"
  ) {
    const previous = new ExactDecimal(event.old_value),
      next = new ExactDecimal(event.new_value);
    direction = next.eq(previous) ? "flat" : next.gt(previous) ? "up" : "down";
    if (previous.gt(0)) delta = next.minus(previous).div(previous).mul(100);
    if (["context_window", "max_output"].includes(field)) unit = "tokens";
  } else if (
    typeof event.old_value === "boolean" &&
    typeof event.new_value === "boolean"
  ) {
    direction =
      event.new_value === event.old_value
        ? "flat"
        : event.new_value
          ? "up"
          : "down";
  } else if (event.event_type.startsWith("new_")) direction = "new";
  const better =
    event.event_type === "price_change"
      ? direction === "down"
      : direction === "up";
  const tone =
    direction === "flat" || direction === "new"
      ? "neutral"
      : better
        ? "positive"
        : "negative";
  const percentage =
    delta == null
      ? null
      : delta.isZero()
        ? "0%"
        : `${delta.gt(0) ? "+" : ""}${delta.abs().lt(0.01) ? delta.toSignificantDigits(2).toString() : delta.toDecimalPlaces(2).toString()}%`;
  return {
    oldLabel,
    newLabel,
    unit,
    direction,
    tone,
    percentage,
    label: field ? humanize(field) : humanize(event.event_type),
  };
}
