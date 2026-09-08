import { afterEach, describe, expect, it } from "vitest";
import { requestId } from "../lib/uuid";

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

describe("requestId", () => {
  const original = globalThis.crypto.randomUUID;
  afterEach(() => {
    Object.defineProperty(globalThis.crypto, "randomUUID", {
      value: original,
      configurable: true,
      writable: true,
    });
  });

  it("uses the platform generator where available", () => {
    expect(requestId()).toMatch(UUID_PATTERN);
  });

  it("falls back to getRandomValues outside secure contexts", () => {
    Object.defineProperty(globalThis.crypto, "randomUUID", {
      value: undefined,
      configurable: true,
      writable: true,
    });
    const first = requestId();
    expect(first).toMatch(UUID_PATTERN);
    expect(first).not.toBe(requestId());
  });
});
