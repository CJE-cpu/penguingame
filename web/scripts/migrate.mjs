import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { neon } from "@neondatabase/serverless";

const databaseUrl = process.env.DATABASE_URL;
if (!databaseUrl) throw new Error("DATABASE_URL is required.");

const root = fileURLToPath(new URL("../", import.meta.url));
const directory = path.join(root, "database", "migrations");
const sql = neon(databaseUrl);

await sql`CREATE TABLE IF NOT EXISTS schema_migrations (
  version TEXT PRIMARY KEY,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)`;

const files = (await readdir(directory))
  .filter((name) => /^\d+.*\.sql$/.test(name))
  .sort();

for (const file of files) {
  const applied = await sql`SELECT 1 FROM schema_migrations WHERE version=${file}`;
  if (applied[0]) {
    console.log(`skip ${file}`);
    continue;
  }
  const contents = await readFile(path.join(directory, file), "utf8");
  const statements = contents
    .split(";")
    .map((statement) => statement.trim())
    .filter(Boolean);
  await sql.transaction([
    ...statements.map((statement) => sql.query(statement)),
    sql`INSERT INTO schema_migrations (version) VALUES (${file})`,
  ]);
  console.log(`applied ${file}`);
}

console.log("database migrations are current");
