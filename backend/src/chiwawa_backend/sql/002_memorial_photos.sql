CREATE TABLE IF NOT EXISTS memorial_photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES google_users (id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    content_type TEXT NOT NULL,
    taken_at TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    address TEXT,
    memo TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memorial_photos_user_taken
    ON memorial_photos (user_id, taken_at);
