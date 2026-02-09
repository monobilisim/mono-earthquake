import sql from '$lib/db';

try {
  await sql`
	CREATE TABLE IF NOT EXISTS earthquakes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    depth REAL NOT NULL,
    md REAL,
    ml REAL,
    mw REAL,
    magnitude REAL,
    location TEXT NOT NULL,
    quality TEXT NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    week INTEGER NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(timestamp, latitude, longitude)
)`;

  await sql`
	CREATE TABLE IF NOT EXISTS webhooks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    type VARCHAR(255) NOT NULL,
    last_sent_at DATETIME,
    created_at TEXT NOT NULL,
    UNIQUE(url),
    UNIQUE(name)
)`;

  await sql`
	CREATE TABLE IF NOT EXISTS polls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL UNIQUE,
    type VARCHAR(255) NOT NULL,
    threshold REAL DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
)`;

  await sql`
	CREATE TABLE IF NOT EXISTS wa_messages (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT 0,
    message TEXT,
    poll_name VARCHAR(255) DEFAULT NULL,
    earthquake_id INTEGER DEFAULT NULL,
    updated_at DATETIME NOT NULL,
    created_at TEXT NOT NULL
)`;

  await sql`
	CREATE TABLE IF NOT EXISTS wa_messages_failed (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    poll_name VARCHAR(255) DEFAULT NULL,
    earthquake_id INTEGER DEFAULT NULL,
    reason TEXT,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
)`;

  await sql`
	CREATE TABLE IF NOT EXISTS groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL UNIQUE,
    polls VARCHAR(255) DEFAULT NULL,
    active BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
)`;

  await sql`
	CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20) DEFAULT NULL,
    groups TEXT DEFAULT NULL,
    user_group TEXT DEFAULT NULL,
    roles TEXT DEFAULT NULL,
    activation_token VARCHAR(255) DEFAULT NULL,
    active BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
)`;

  await sql`
	CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_token TEXT NOT NULL UNIQUE,
    expiration_date DATETIME NOT NULL DEFAULT (DATETIME('now', '+7 days')),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
)`;

  await sql`
	CREATE TABLE IF NOT EXISTS user_groups (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	name TEXT NOT NULL UNIQUE,
	tenant TEXT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
)`;
} catch (error) {
  console.error('Error creating tables:', error);
}
