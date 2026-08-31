import type { NextConfig } from "next";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { parseEnv } from "node:util";
const envPath = resolve(process.cwd(), "../../.env");
if (existsSync(envPath)) {
  for (const [key, value] of Object.entries(
    parseEnv(readFileSync(envPath, "utf8")),
  )) {
    if (process.env[key] === undefined) process.env[key] = value;
  }
}
const config: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Frame-Options", value: "DENY" },
        ],
      },
    ];
  },
};
export default config;
