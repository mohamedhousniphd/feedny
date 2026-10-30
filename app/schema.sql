CREATE TABLE IF NOT EXISTS feedbacks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    device_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    included_in_analysis BOOLEAN DEFAULT 0,
    emotion INTEGER DEFAULT NULL,
    teacher_id INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS device_limits (
    device_id TEXT PRIMARY KEY,
    feedback_count INTEGER DEFAULT 0,
    last_feedback TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS teachers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    unique_code TEXT UNIQUE NOT NULL,
    credits INTEGER DEFAULT 3,
    is_admin BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payment_receipts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (teacher_id) REFERENCES teachers (id)
);

CREATE TABLE IF NOT EXISTS client_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event TEXT NOT NULL,
    teacher_id INTEGER,
    device_id TEXT,
    device_type TEXT,
    browser TEXT,
    os TEXT,
    user_agent TEXT,
    platform TEXT,
    language TEXT,
    timezone TEXT,
    screen TEXT,
    viewport TEXT,
    connection_type TEXT,
    network_type TEXT,
    downlink REAL,
    rtt REAL,
    save_data BOOLEAN,
    touch BOOLEAN,
    memory_gb REAL,
    cores REAL,
    country TEXT,
    referrer TEXT,
    fill_seconds REAL,
    first_input_seconds REAL,
    typing_seconds REAL,
    total_seconds REAL,
    keystrokes INTEGER,
    backspaces INTEGER,
    pasted BOOLEAN,
    paste_chars INTEGER,
    idle_seconds REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_client_events_teacher
    ON client_events (teacher_id, event, created_at);

CREATE TABLE IF NOT EXISTS analysis_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER NOT NULL,
    summary TEXT NOT NULL,
    wordcloud_image TEXT,
    feedback_count INTEGER DEFAULT 0,
    context TEXT,
    technical_context TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (teacher_id) REFERENCES teachers (id)
);
