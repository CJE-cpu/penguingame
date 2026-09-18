import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = fileURLToPath(new URL("../", import.meta.url));
const children = [
  spawn(process.execPath, ["server/index.mjs"], {
    cwd: root,
    stdio: "inherit",
    env: { ...process.env, PORT: process.env.API_PORT || "3001" },
  }),
  spawn(process.execPath, [path.join(root, "node_modules/vite/bin/vite.js")], {
    cwd: root,
    stdio: "inherit",
  }),
];
let stopping = false;
const stop = (code = 0) => {
  if (stopping) return;
  stopping = true;
  for (const child of children) child.kill();
  process.exitCode = code;
};
for (const child of children) {
  child.on("error", () => stop(1));
  child.on("exit", (code) => stop(code ?? 0));
}
process.on("SIGINT", () => stop());
process.on("SIGTERM", () => stop());
