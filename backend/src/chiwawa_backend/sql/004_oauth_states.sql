CREATE TABLE IF NOT EXISTS oauth_states (
    value TEXT PRIMARY KEY,
    expires_at TEXT NOT NULL,
    issued_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_oauth_states_expires
    ON oauth_states (expires_at);
