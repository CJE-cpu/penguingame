import express from "express";
import helmet from "helmet";
import cookieParser from "cookie-parser";
import { rateLimit } from "express-rate-limit";
import { DatabaseSync } from "node:sqlite";
import {
  randomBytes,
  randomUUID,
  scrypt,
  timingSafeEqual,
  createHash,
} from "node:crypto";
import { promisify } from "node:util";
import { mkdirSync, existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const derive = promisify(scrypt);
const root = fileURLToPath(new URL("../", import.meta.url));
const cookieName = "penguin_session";
const duration = 7 * 24 * 60 * 60 * 1000;
const hash = (value) => createHash("sha256").update(value).digest("hex");
const publicUser = (user) => ({
  id: user.id,
  nickname: user.nickname,
  email: user.email,
});
const normalize = (text) =>
  typeof text === "string" ? text.normalize("NFC").trim() : "";
const fail = (status, message) => Object.assign(new Error(message), { status });
const number = (value, min, max) =>
  Number.isInteger(value) && value >= min && value <= max;

export function demoData() {
  const names = [
    "눈송이",
    "포근한 펭귄",
    "빙하 탐험가",
    "물고기 수집가",
    "파란 바다",
    "남극의 오후",
  ];
  const dates = Array.from({ length: 8 }, (_, i) =>
    new Date(Date.now() - (7 - i) * 24 * 60 * 60 * 1000).toISOString(),
  );
  const records = [420, 680, 590, 950, 1120, 1030, 1380, 1680].map(
    (score, i) => ({
      id: `demo-${i}`,
      score,
      fish: i >= 6 ? 30 : Math.min(30, 10 + i * 3),
      rescued: Math.min(3, Math.floor(i / 2)),
      seconds: 160 + i * 20,
      cleared: i >= 6,
      date: dates[i],
      source: "demo",
    }),
  );
  return {
    demo: true,
    summary: { best: 1680, average: 981, games: 8, clears: 2, rank: 3 },
    records,
    trend: records,
    leaderboard: names.map((nickname, i) => ({
      rank: i + 1,
      nickname,
      score: [2240, 1950, 1680, 1470, 1180, 920][i],
      cleared: i < 4,
      fish: 30 - i * 2,
      rescued: i < 4 ? 3 : 2,
      date: dates[7],
      isMe: i === 2,
    })),
  };
}

export function createApp({
  dbPath = process.env.DB_PATH || path.join(root, ".data", "penguin.sqlite"),
  appOrigin = process.env.APP_ORIGIN,
  production = process.env.NODE_ENV === "production",
} = {}) {
  if (production && !appOrigin)
    throw new Error("APP_ORIGIN is required in production.");
  if (dbPath !== ":memory:")
    mkdirSync(path.dirname(dbPath), { recursive: true });
  const db = new DatabaseSync(dbPath, { timeout: 5000 });
  db.exec(`PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;
    CREATE TABLE IF NOT EXISTS users (
      id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE COLLATE NOCASE,
      nickname TEXT NOT NULL, salt TEXT NOT NULL, password_hash TEXT NOT NULL, created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS sessions (
      token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, expires_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS scores (
      id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      run_id TEXT NOT NULL, score INTEGER NOT NULL, fish INTEGER NOT NULL, rescued INTEGER NOT NULL,
      seconds INTEGER NOT NULL, cleared INTEGER NOT NULL, played_at TEXT NOT NULL,
      source TEXT NOT NULL DEFAULT 'desktop', UNIQUE(user_id,run_id)
    );
    CREATE INDEX IF NOT EXISTS scores_user_date ON scores(user_id,played_at);
    CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions(expires_at);`);
  const app = express();
  app.disable("x-powered-by");
  if (process.env.TRUST_PROXY === "1") app.set("trust proxy", 1);
  app.use(
    helmet({
      contentSecurityPolicy: production
        ? {
            directives: {
              defaultSrc: ["'self'"],
              scriptSrc: ["'self'"],
              styleSrc: ["'self'", "'unsafe-inline'"],
              imgSrc: ["'self'", "data:"],
              fontSrc: ["'self'"],
              connectSrc: ["'self'"],
              upgradeInsecureRequests: appOrigin?.startsWith("https:")
                ? []
                : null,
            },
          }
        : false,
    }),
  );
  app.use(express.json({ limit: "512kb" }));
  app.use(cookieParser());
  app.use("/api", (req, res, next) => {
    res.set("Cache-Control", "no-store");
    if (["POST", "PUT", "PATCH", "DELETE"].includes(req.method)) {
      const origin = req.get("origin");
      const expected = appOrigin || `${req.protocol}://${req.get("host")}`;
      if (!origin || origin !== expected)
        return next(
          fail(
            403,
            "허용되지 않은 요청입니다. 같은 사이트에서 다시 시도해 주세요.",
          ),
        );
    }
    next();
  });
  const authLimiter = rateLimit({
    windowMs: 10 * 60 * 1000,
    limit: 20,
    standardHeaders: "draft-8",
    legacyHeaders: false,
    message: {
      error: "잠시 후 다시 로그인해 주세요. 요청 횟수를 초과했습니다.",
    },
  });
  const sessionOptions = {
    httpOnly: true,
    sameSite: "lax",
    secure: !!appOrigin?.startsWith("https:"),
    path: "/",
    maxAge: duration,
  };
  const startSession = (req, res, user) => {
    if (req.cookies[cookieName])
      db.prepare("DELETE FROM sessions WHERE token_hash=?").run(
        hash(req.cookies[cookieName]),
      );
    db.prepare("DELETE FROM sessions WHERE expires_at<?").run(Date.now());
    const token = randomBytes(32).toString("hex");
    db.prepare("INSERT INTO sessions VALUES (?,?,?)").run(
      hash(token),
      user.id,
      Date.now() + duration,
    );
    res.cookie(cookieName, token, sessionOptions);
  };
  const authenticate = (req, res, next) => {
    const token = req.cookies[cookieName];
    if (typeof token !== "string" || token.length !== 64)
      return next(fail(401, "로그인한 뒤 이용할 수 있습니다."));
    const user = db
      .prepare(
        `SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id
                            WHERE s.token_hash=? AND s.expires_at>?`,
      )
      .get(hash(token), Date.now());
    if (!user)
      return next(
        fail(401, "로그인 세션이 만료되었습니다. 다시 로그인해 주세요."),
      );
    req.user = user;
    next();
  };
  app.get("/api/health", (_, res) => res.json({ ok: true }));
  app.post("/api/auth/register", authLimiter, async (req, res) => {
    const email = normalize(req.body.email).toLowerCase();
    const nickname = normalize(req.body.nickname);
    const password = req.body.password;
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) || email.length > 254)
      throw fail(400, "올바른 이메일을 입력해 주세요.");
    if (
      nickname.length < 2 ||
      nickname.length > 16 ||
      /[\p{C}]/u.test(nickname)
    )
      throw fail(400, "닉네임은 2~16자로 입력해 주세요.");
    if (
      typeof password !== "string" ||
      password.length < 8 ||
      password.length > 128
    )
      throw fail(400, "비밀번호는 8~128자로 입력해 주세요.");
    if (db.prepare("SELECT id FROM users WHERE email=?").get(email))
      throw fail(409, "이미 가입한 이메일입니다. 로그인해 주세요.");
    const salt = randomBytes(16).toString("hex");
    const passwordHash = await derive(password, salt, 32, {
      N: 16384,
      r: 8,
      p: 1,
      maxmem: 64 * 1024 * 1024,
    });
    const user = { id: randomUUID(), email, nickname };
    try {
      db.prepare("INSERT INTO users VALUES (?,?,?,?,?,?)").run(
        user.id,
        email,
        nickname,
        salt,
        passwordHash.toString("hex"),
        new Date().toISOString(),
      );
    } catch (error) {
      if (String(error.message).includes("UNIQUE"))
        throw fail(409, "이미 가입한 이메일입니다.");
      throw error;
    }
    startSession(req, res, user);
    res.status(201).json({ user });
  });
  app.post("/api/auth/login", authLimiter, async (req, res) => {
    const email = normalize(req.body.email).toLowerCase();
    if (typeof req.body.password !== "string" || req.body.password.length > 128)
      throw fail(400, "이메일과 비밀번호를 확인해 주세요.");
    const user = db.prepare("SELECT * FROM users WHERE email=?").get(email);
    const result = await derive(
      req.body.password,
      user?.salt || "00000000000000000000000000000000",
      32,
      { N: 16384, r: 8, p: 1, maxmem: 64 * 1024 * 1024 },
    );
    const expected = Buffer.from(user?.password_hash || "0".repeat(64), "hex");
    if (!timingSafeEqual(result, expected) || !user)
      throw fail(401, "이메일 또는 비밀번호가 일치하지 않습니다.");
    startSession(req, res, user);
    res.json({ user: publicUser(user) });
  });
  app.get("/api/auth/me", (req, res, next) => {
    if (!req.cookies[cookieName]) return res.json({ user: null });
    authenticate(req, res, (error) =>
      error
        ? res.json({ user: null })
        : res.json({ user: publicUser(req.user) }),
    );
  });
  app.post("/api/auth/logout", (req, res) => {
    if (typeof req.cookies[cookieName] === "string")
      db.prepare("DELETE FROM sessions WHERE token_hash=?").run(
        hash(req.cookies[cookieName]),
      );
    res.clearCookie(cookieName, { ...sessionOptions, maxAge: undefined });
    res.json({ ok: true });
  });
  const cutoff = (range) =>
    new Date(
      range === "week"
        ? Date.now() - 7 * 86400000
        : range === "month"
          ? Date.now() - 30 * 86400000
          : 0,
    ).toISOString();
  const leaderboard = (range, userId) =>
    db
      .prepare(
        `
    WITH best AS (SELECT s.*,u.nickname,ROW_NUMBER() OVER(PARTITION BY s.user_id ORDER BY s.score DESC,s.cleared DESC,s.played_at ASC) n
      FROM scores s JOIN users u ON u.id=s.user_id WHERE s.played_at>=?)
    SELECT user_id,nickname,score,fish,rescued,cleared,played_at FROM best WHERE n=1
    ORDER BY score DESC,cleared DESC,played_at ASC,user_id ASC`,
      )
      .all(cutoff(range))
      .map((row, i) => ({
        rank: i + 1,
        nickname: row.nickname,
        score: row.score,
        fish: row.fish,
        rescued: row.rescued,
        cleared: !!row.cleared,
        date: row.played_at,
        isMe: row.user_id === userId,
      }));
  app.get("/api/leaderboard", (req, res) =>
    res.json({ leaderboard: leaderboard(req.query.range).slice(0, 50) }),
  );
  app.get("/api/demo", (_, res) => res.json(demoData()));
  app.get("/api/dashboard", authenticate, (req, res) => {
    const rows = db
      .prepare(
        "SELECT * FROM scores WHERE user_id=? AND played_at>=? ORDER BY played_at ASC,id ASC",
      )
      .all(req.user.id, cutoff(req.query.range));
    const records = rows.map((r) => ({
      id: r.id,
      score: r.score,
      fish: r.fish,
      rescued: r.rescued,
      seconds: r.seconds,
      cleared: !!r.cleared,
      date: r.played_at,
      source: r.source,
    }));
    const ranks = leaderboard(req.query.range, req.user.id);
    const summary = {
      games: rows.length,
      best: rows.length ? Math.max(...rows.map((r) => r.score)) : 0,
      average: rows.length
        ? Math.round(rows.reduce((sum, r) => sum + r.score, 0) / rows.length)
        : 0,
      clears: rows.filter((r) => r.cleared).length,
      rank: ranks.find((r) => r.isMe)?.rank || null,
    };
    res.json({
      demo: false,
      summary,
      records: records.reverse(),
      trend: [...records].reverse().slice(-30),
      leaderboard: ranks.slice(0, 50),
    });
  });
  app.post(
    "/api/scores/import",
    rateLimit({
      windowMs: 60000,
      limit: 30,
      legacyHeaders: false,
      message: { error: "업로드가 너무 잦습니다. 잠시 후 다시 시도해 주세요." },
    }),
    authenticate,
    (req, res) => {
      const records = req.body.records;
      if (!Array.isArray(records) || records.length < 1 || records.length > 100)
        throw fail(400, "한 번에 1~100개의 기록을 가져올 수 있습니다.");
      const entries = records.map((r) => {
        if (
          !r ||
          typeof r !== "object" ||
          typeof r.run !== "string" ||
          r.run.length < 1 ||
          r.run.length > 100 ||
          !number(r.score, 1, 20000) ||
          !number(r.fish, 0, 30) ||
          !number(r.rescued, 0, 3) ||
          !number(r.seconds, 0, 172800) ||
          typeof r.cleared !== "boolean" ||
          typeof r.date !== "string" ||
          r.date.length > 40 ||
          !Number.isFinite(Date.parse(r.date)) ||
          Date.parse(r.date) > Date.now() + 86400000 ||
          Date.parse(r.date) < 0 ||
          (r.cleared && (r.fish !== 30 || r.rescued !== 3))
        )
          throw fail(
            400,
            "기록 형식이 올바르지 않습니다. 게임에서 저장한 scores.json을 선택해 주세요.",
          );
        return { ...r, date: new Date(r.date).toISOString() };
      });
      const count = db
        .prepare("SELECT COUNT(*) total FROM scores WHERE user_id=?")
        .get(req.user.id).total;
      const existing = db.prepare(
        "SELECT 1 FROM scores WHERE user_id=? AND run_id=?",
      );
      const fresh = new Set(
        entries
          .filter((r) => !existing.get(req.user.id, r.run))
          .map((r) => r.run),
      ).size;
      if (count + fresh > 1000)
        throw fail(
          400,
          "계정당 최대 1,000개의 탐험 기록을 저장할 수 있습니다.",
        );
      const insert = db.prepare(`INSERT INTO scores VALUES (?,?,?,?,?,?,?,?,?,?)
      ON CONFLICT(user_id,run_id) DO UPDATE SET score=excluded.score,fish=MAX(scores.fish,excluded.fish),
      rescued=MAX(scores.rescued,excluded.rescued),seconds=MAX(scores.seconds,excluded.seconds),
      cleared=MAX(scores.cleared,excluded.cleared),played_at=excluded.played_at WHERE excluded.score>=scores.score`);
      let changed = 0;
      db.exec("BEGIN IMMEDIATE");
      try {
        for (const r of entries)
          changed += insert.run(
            randomUUID(),
            req.user.id,
            r.run,
            r.score,
            r.fish,
            r.rescued,
            r.seconds,
            Number(r.cleared),
            r.date,
            "desktop",
          ).changes;
        db.exec("COMMIT");
      } catch (error) {
        db.exec("ROLLBACK");
        throw error;
      }
      res.json({
        imported: changed,
        total: db
          .prepare("SELECT COUNT(*) total FROM scores WHERE user_id=?")
          .get(req.user.id).total,
      });
    },
  );
  app.get("/api/download", (_, res, next) => {
    const exe =
      process.env.GAME_EXE_PATH ||
      path.resolve(root, "../pygame/AntarcticPenguin.exe");
    if (!existsSync(exe))
      return next(
        fail(404, "실행 파일이 없습니다. GitHub에서 게임을 내려받아 주세요."),
      );
    res.download(exe, "AntarcticPenguin.exe");
  });
  app.use("/api", (_, res) =>
    res.status(404).json({ error: "요청한 기능을 찾을 수 없습니다." }),
  );
  if (existsSync(path.join(root, "dist", "index.html"))) {
    app.use(
      express.static(path.join(root, "dist"), { maxAge: "1h", index: false }),
    );
    app.get("/{*path}", (_, res) =>
      res.sendFile(path.join(root, "dist", "index.html")),
    );
  }
  app.use((error, req, res, next) => {
    if (res.headersSent) return next(error);
    const status = error.status || 500;
    if (status >= 500) console.error("API error:", error.code || error.name);
    res
      .status(status)
      .json({
        error:
          status === 413
            ? "파일이 너무 큽니다. 512KB 이하의 점수 파일을 사용해 주세요."
            : status >= 500
              ? "서버 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
              : error.message,
      });
  });
  return { app, db };
}
