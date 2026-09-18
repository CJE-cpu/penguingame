import { defineConfig } from "@playwright/test";
import { existsSync } from "node:fs";
import path from "node:path";

const edge = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:5174",
    viewport: { width: 1366, height: 900 },
    launchOptions: {
      ...(process.env.BROWSER_PATH
        ? { executablePath: process.env.BROWSER_PATH }
        : existsSync(edge)
          ? { executablePath: edge }
          : {}),
    },
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "node scripts/dev.mjs",
    url: "http://127.0.0.1:5174/api/health",
    timeout: 30000,
    reuseExistingServer: false,
    env: {
      API_PORT: "3002",
      WEB_PORT: "5174",
      DB_PATH: path.resolve(".data/e2e.sqlite"),
    },
  },
});
