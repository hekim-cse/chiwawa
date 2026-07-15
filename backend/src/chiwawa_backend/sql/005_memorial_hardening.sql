ALTER TABLE memorial_photos
    ADD COLUMN taken_at_utc TEXT NOT NULL DEFAULT '';

ALTER TABLE memorial_photos
    ADD COLUMN local_date TEXT NOT NULL DEFAULT '';

ALTER TABLE memorial_photos
    ADD COLUMN size_bytes INTEGER NOT NULL DEFAULT 0 CHECK (size_bytes >= 0);

UPDATE memorial_photos
SET taken_at_utc = CASE
    WHEN substr(taken_at, -1) = 'Z'
        OR substr(taken_at, -6, 1) IN ('+', '-')
    THEN strftime('%Y-%m-%dT%H:%M:%fZ', taken_at)
    ELSE strftime('%Y-%m-%dT%H:%M:%fZ', taken_at, '-9 hours')
END
WHERE taken_at_utc = '';

UPDATE memorial_photos
SET local_date = CASE
    WHEN substr(taken_at, -1) = 'Z'
        OR substr(taken_at, -6, 1) IN ('+', '-')
    THEN date(taken_at, '+9 hours')
    ELSE date(taken_at)
END
WHERE local_date = '';

CREATE TABLE IF NOT EXISTS upload_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES google_users (id) ON DELETE CASCADE,
    size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_upload_events_user_created
    ON upload_events (user_id, created_at);

CREATE TABLE IF NOT EXISTS upload_leases (
    lease_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES google_users (id) ON DELETE CASCADE,
    reserved_bytes INTEGER NOT NULL CHECK (reserved_bytes >= 0),
    acquired_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_upload_leases_user_expires
    ON upload_leases (user_id, expires_at);

CREATE INDEX IF NOT EXISTS idx_upload_leases_expires
    ON upload_leases (expires_at);

CREATE INDEX IF NOT EXISTS idx_memorial_photos_user_local_date_utc
    ON memorial_photos (user_id, local_date, taken_at_utc);
