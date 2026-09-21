import { createPostgresApp } from "../server/postgres-app.mjs";

const { app } = createPostgresApp();

export default app;
