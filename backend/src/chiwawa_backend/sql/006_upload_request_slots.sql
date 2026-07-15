CREATE TABLE IF NOT EXISTS upload_request_slots (
    slot_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES google_users (id) ON DELETE CASCADE,
    acquired_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_upload_request_slots_user_expires
    ON upload_request_slots (user_id, expires_at);

CREATE INDEX IF NOT EXISTS idx_upload_request_slots_expires
    ON upload_request_slots (expires_at);
