import { describe, expect, it } from "vitest";
import { money, tokens } from "../lib/format";
describe("evidence formatting", () => {
  it("distinguishes unknown from explicitly free prices", () => {
    expect(money(null)).toBe("Unknown");
    expect(money("0")).toBe("$0");
  });
  it("keeps small price precision", () => {
    expect(money("0.00001234")).toBe("$0.00001234");
    expect(money("0.000000000001")).not.toBe("$0");
  });
  it("formats context without inventing missing limits", () => {
    expect(tokens(null)).toBe("Unknown");
    expect(tokens(128000)).toBe("128K");
    expect(tokens(1000000)).toBe("1M");
  });
});
