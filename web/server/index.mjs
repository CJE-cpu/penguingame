import { createApp } from "./app.mjs";

const { app, db } = createApp();
const port = Number(process.env.PORT || 3001);
const host = process.env.HOST || "127.0.0.1";
const server = app.listen(port, host, () =>
  console.log(`Penguin API: http://${host}:${port}`),
);
const close = () =>
  server.close(() => {
    db.close();
    process.exit(0);
  });
process.on("SIGINT", close);
process.on("SIGTERM", close);
