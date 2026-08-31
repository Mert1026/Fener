import { createHmac, timingSafeEqual } from "node:crypto";

export function sameOrigin(request: Request): boolean {
  // Next's development request URL can normalize 127.0.0.1 to localhost.
  // The browser's Origin must instead match the actual HTTP Host exactly.
  const origin = request.headers.get("origin");
  if (!origin) return false;
  try {
    const url = new URL(origin);
    const trusted = process.env.FENER_WEB_ORIGIN;
    const allowed = trusted
      ? url.origin === new URL(trusted).origin
      : ["127.0.0.1", "localhost", "[::1]"].includes(url.hostname);
    return (
      allowed &&
      ["http:", "https:"].includes(url.protocol) &&
      url.host === request.headers.get("host") &&
      url.origin === origin
    );
  } catch {
    return false;
  }
}

export function createSession(key: string, now = Date.now()): string {
  const expires = String(Math.floor(now / 1000) + 28800);
  const signature = createHmac("sha256", key)
    .update(`fener-v2:${expires}`)
    .digest("hex");
  return `${expires}.${signature}`;
}

export function validSession(
  token: string,
  key: string,
  now = Date.now(),
): boolean {
  if (!key || !/^\d{10}\.[a-f0-9]{64}$/.test(token)) return false;
  const [expires, signature] = token.split(".");
  const seconds = Math.floor(now / 1000);
  if (Number(expires) <= seconds || Number(expires) > seconds + 28800)
    return false;
  const expected = createHmac("sha256", key)
    .update(`fener-v2:${expires}`)
    .digest("hex");
  return timingSafeEqual(Buffer.from(signature), Buffer.from(expected));
}

export async function boundedBody(
  request: Request,
  maximum: number,
): Promise<string> {
  if (!request.body) return "";
  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > maximum) {
        await reader.cancel();
        throw new Error("Request too large");
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  return Buffer.concat(chunks).toString("utf8");
}
