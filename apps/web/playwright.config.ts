import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  timeout: 60000,
  workers: 1,
  use: {
    baseURL: process.env.FENER_E2E_URL ?? "http://127.0.0.1:3000",
    trace: "retain-on-failure",
  },
});
