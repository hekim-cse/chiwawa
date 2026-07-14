CREATE TABLE IF NOT EXISTS google_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    google_sub TEXT NOT NULL UNIQUE,
    email TEXT,
    name TEXT,
    picture TEXT,
    created_at TEXT NOT NULL,
    last_login_at TEXT NOT NULL
);
