import test from "node:test";
import assert from "node:assert/strict";
import { once } from "node:events";
import { createApp } from "./app.mjs";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

async function server(dbPath = ":memory:") {
  const state = createApp({ dbPath });
  const listener = state.app.listen(0, "127.0.0.1");
  await once(listener, "listening");
  const base = `http://127.0.0.1:${listener.address().port}`;
  return {
    ...state,
    base,
    close: async () => {
      await new Promise((resolve) => listener.close(resolve));
      state.db.close();
    },
  };
}
async function request(
  state,
  url,
  { cookie, body, method = "GET", origin = state.base } = {},
) {
  const response = await fetch(state.base + url, {
    method,
    headers: {
      Origin: origin,
      "Content-Type": "application/json",
      ...(cookie ? { Cookie: cookie } : {}),
    },
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });
  return {
    status: response.status,
    data: await response.json(),
    cookie: response.headers.get("set-cookie")?.split(";")[0],
    headers: response.headers,
  };
}
async function register(state, email = "penguin@example.test") {
  return request(state, "/api/auth/register", {
    method: "POST",
    body: { nickname: "눈송이", email, password: "Penguin-test-123" },
  });
}
const entry = (overrides = {}) => ({
  run: "first-run",
  name: "눈송이",
  score: 1200,
  fish: 30,
  rescued: 3,
  seconds: 320,
  cleared: true,
  date: new Date().toISOString(),
  ...overrides,
});

test("registration hashes passwords, creates an HttpOnly session and persists after reopening", async () => {
  const directory = mkdtempSync(path.join(tmpdir(), "penguin-api-"));
  const dbPath = path.join(directory, "scores.sqlite");
  let state = await server(dbPath);
  try {
    const result = await register(state);
    assert.equal(result.status, 201);
    assert.match(result.headers.get("set-cookie"), /HttpOnly/);
    assert.match(result.headers.get("set-cookie"), /SameSite=Lax/);
    const stored = state.db.prepare("SELECT * FROM users").get();
    assert.notEqual(stored.password_hash, "Penguin-test-123");
    assert.equal(stored.password_hash.length, 64);
    assert.equal(
      (await request(state, "/api/auth/me", { cookie: result.cookie })).data
        .user.nickname,
      "눈송이",
    );
    assert.equal((await register(state)).status, 409);
    await state.close();
    state = await server(dbPath);
    assert.equal(
      (await request(state, "/api/auth/me", { cookie: result.cookie })).data
        .user.email,
      "penguin@example.test",
    );
  } finally {
    await state.close();
    rmSync(directory, { recursive: true, force: true });
  }
});
test("login failures, logout and missing sessions do not expose protected records", async () => {
  const state = await server();
  try {
    const registered = await register(state);
    assert.equal((await request(state, "/api/dashboard")).status, 401);
    assert.equal(
      (
        await request(state, "/api/auth/login", {
          method: "POST",
          body: { email: "penguin@example.test", password: "incorrect" },
        })
      ).status,
      401,
    );
    const logged = await request(state, "/api/auth/login", {
      method: "POST",
      body: { email: "PENGUIN@example.test", password: "Penguin-test-123" },
    });
    assert.equal(logged.status, 200);
    assert.equal(
      (await request(state, "/api/dashboard", { cookie: logged.cookie }))
        .status,
      200,
    );
    assert.equal(
      (await request(state, "/api/dashboard", { cookie: registered.cookie }))
        .status,
      200,
    );
    await request(state, "/api/auth/logout", {
      method: "POST",
      cookie: logged.cookie,
      body: {},
    });
    assert.equal(
      (await request(state, "/api/dashboard", { cookie: logged.cookie }))
        .status,
      401,
    );
    assert.equal(
      (await request(state, "/api/auth/me", { cookie: logged.cookie })).data
        .user,
      null,
    );
  } finally {
    await state.close();
  }
});
test("score imports update one run, preserve higher scores and isolate account histories", async () => {
  const state = await server();
  try {
    const a = await register(state, "a@example.test");
    const b = await register(state, "b@example.test");
    const send = (records) =>
      request(state, "/api/scores/import", {
        method: "POST",
        cookie: a.cookie,
        body: { records },
      });
    assert.equal((await send([entry()])).status, 200);
    await send([entry({ score: 1300 })]);
    await send([entry({ score: 800 })]);
    await send([
      entry({
        run: "second-run",
        score: 500,
        fish: 15,
        rescued: 1,
        cleared: false,
      }),
    ]);
    const dashboard = (
      await request(state, "/api/dashboard", { cookie: a.cookie })
    ).data;
    assert.equal(dashboard.summary.games, 2);
    assert.equal(dashboard.summary.best, 1300);
    assert.equal(dashboard.summary.average, 900);
    assert.equal(dashboard.summary.clears, 1);
    assert.equal(dashboard.summary.rank, 1);
    assert.equal(
      (await request(state, "/api/dashboard", { cookie: b.cookie })).data
        .records.length,
      0,
    );
    const publicRanks = (await request(state, "/api/leaderboard")).data
      .leaderboard;
    assert.equal(publicRanks.length, 1);
    assert.equal(publicRanks[0].score, 1300);
    assert.equal("email" in publicRanks[0], false);
  } finally {
    await state.close();
  }
});
test("invalid and mixed imports are rejected atomically and cross-site writes fail", async () => {
  const state = await server();
  try {
    const account = await register(state);
    const opts = { method: "POST", cookie: account.cookie };
    assert.equal(
      (
        await request(state, "/api/scores/import", {
          ...opts,
          body: { records: [entry(), entry({ run: "invalid", score: -10 })] },
        })
      ).status,
      400,
    );
    assert.equal(
      (await request(state, "/api/dashboard", { cookie: account.cookie })).data
        .summary.games,
      0,
    );
    assert.equal(
      (
        await request(state, "/api/scores/import", {
          ...opts,
          body: { records: [entry({ fish: 20 })] },
        })
      ).status,
      400,
    );
    assert.equal(
      (
        await request(state, "/api/scores/import", {
          ...opts,
          origin: "https://other-site.example",
          body: { records: [entry()] },
        })
      ).status,
      403,
    );
    assert.equal(
      (
        await request(state, "/api/auth/register", {
          method: "POST",
          body: { email: "invalid", password: "short", nickname: "a" },
        })
      ).status,
      400,
    );
    assert.equal(
      (
        await request(state, "/api/scores/import", {
          ...opts,
          body: { records: [] },
        })
      ).status,
      400,
    );
  } finally {
    await state.close();
  }
});
test("time filters affect trends and ranks, and demo data never enters the real database", async () => {
  const state = await server();
  try {
    const account = await register(state);
    await request(state, "/api/scores/import", {
      method: "POST",
      cookie: account.cookie,
      body: { records: [entry({ date: "2020-01-01T00:00:00.000Z" })] },
    });
    assert.equal(
      (
        await request(state, "/api/dashboard?range=week", {
          cookie: account.cookie,
        })
      ).data.records.length,
      0,
    );
    assert.equal(
      (await request(state, "/api/dashboard", { cookie: account.cookie })).data
        .records.length,
      1,
    );
    assert.equal((await request(state, "/api/demo")).data.demo, true);
    assert.equal(
      (await request(state, "/api/leaderboard")).data.leaderboard.length,
      1,
    );
    state.db.prepare("UPDATE sessions SET expires_at=0").run();
    assert.equal(
      (await request(state, "/api/dashboard", { cookie: account.cookie }))
        .status,
      401,
    );
  } finally {
    await state.close();
  }
});
