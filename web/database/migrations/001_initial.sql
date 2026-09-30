CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  nickname TEXT NOT NULL,
  salt TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS users_nickname_unique
  ON users (LOWER(nickname));

CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at BIGINT NOT NULL
);

CREATE INDEX IF NOT EXISTS sessions_expiry
  ON sessions (expires_at);

CREATE TABLE IF NOT EXISTS scores (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  run_id TEXT NOT NULL,
  score INTEGER NOT NULL CHECK (score >= 0),
  fish INTEGER NOT NULL CHECK (fish BETWEEN 0 AND 30),
  rescued INTEGER NOT NULL CHECK (rescued BETWEEN 0 AND 3),
  seconds INTEGER NOT NULL CHECK (seconds >= 0),
  cleared BOOLEAN NOT NULL,
  played_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  source TEXT NOT NULL DEFAULT 'desktop' CHECK (source IN ('desktop', 'browser')),
  UNIQUE (user_id, run_id)
);

CREATE INDEX IF NOT EXISTS scores_user_date
  ON scores (user_id, played_at DESC);

CREATE INDEX IF NOT EXISTS scores_ranking
  ON scores (score DESC, cleared DESC, played_at ASC);
