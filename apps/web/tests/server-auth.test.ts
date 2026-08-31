import { describe, expect, it } from "vitest";
import { createSession, sameOrigin, validSession } from "../lib/server-auth";

describe("signed local sessions", () => {
  it("checks the browser origin against the real Host header", () => {
    const request = (origin: string, host = "127.0.0.1:3000") =>
      new Request("http://localhost:3000/api/session", {
        headers: { origin, host },
      });
    expect(sameOrigin(request("http://127.0.0.1:3000"))).toBe(true);
    expect(sameOrigin(request("http://localhost:3000"))).toBe(false);
    expect(sameOrigin(request("https://attacker.example"))).toBe(false);
    expect(
      sameOrigin(request("http://attacker.example", "attacker.example")),
    ).toBe(false);
  });
  it("rejects tampering, expiry and rotated credentials", () => {
    const now = 1788170400000;
    const token = createSession("fixture-key", now);
    expect(validSession(token, "fixture-key", now)).toBe(true);
    expect(validSession(token, "fixture-key", now + 28800000)).toBe(false);
    expect(validSession(token, "rotated-key", now)).toBe(false);
    expect(validSession(token.replace(/^\d/, "9"), "fixture-key", now)).toBe(
      false,
    );
    expect(validSession("", "", now)).toBe(false);
  });
});
