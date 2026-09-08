export function requestId(): string {
  // crypto.randomUUID() only exists in secure contexts (HTTPS or localhost).
  // The UI is also served over plain HTTP on tailnet origins (e.g.
  // http://fener:3000), so build an RFC 4122 v4 identifier from
  // getRandomValues there instead; that API is available everywhere.
  if (typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}
