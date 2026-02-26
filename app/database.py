import sqlite3
from contextlib import contextmanager
from typing import Optional
from datetime import datetime
import uuid


DATABASE_URL = "feedny.db"


@contextmanager
def get_db():
    """Context manager for database connections with WAL mode for better concurrency."""
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    try:
        # Enable WAL mode for better performance
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize the database with required tables and run migrations."""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedbacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                device_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                included_in_analysis BOOLEAN DEFAULT 0,
                emotion INTEGER DEFAULT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS device_limits (
                device_id TEXT PRIMARY KEY,
                feedback_count INTEGER DEFAULT 0,
                last_feedback TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()
        
        # Migration: Add emotion column if it doesn't exist
        try:
            conn.execute("SELECT emotion FROM feedbacks LIMIT 1")
        except sqlite3.OperationalError:
            conn.execute("ALTER TABLE feedbacks ADD COLUMN emotion INTEGER DEFAULT NULL")
            conn.commit()

        # Migration: Add teacher_id column if it doesn't exist
        try:
            conn.execute("SELECT teacher_id FROM feedbacks LIMIT 1")
        except sqlite3.OperationalError:
            conn.execute("ALTER TABLE feedbacks ADD COLUMN teacher_id INTEGER DEFAULT 1")
            conn.commit()
        
        # Create teachers table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS teachers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                unique_code TEXT UNIQUE NOT NULL,
                credits INTEGER DEFAULT 3,
                is_admin BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS payment_receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (teacher_id) REFERENCES teachers (id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analysis_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id INTEGER NOT NULL,
                summary TEXT NOT NULL,
                wordcloud_image TEXT,
                feedback_count INTEGER DEFAULT 0,
                context TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (teacher_id) REFERENCES teachers (id)
            )
        """)
        conn.commit()


def insert_feedback(content: str, device_id: str, emotion: Optional[int] = None, teacher_id: int = 1) -> int:
    """Insert a new feedback and return its ID."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO feedbacks (content, device_id, emotion, teacher_id) VALUES (?, ?, ?, ?)",
            (content, device_id, emotion, teacher_id)
        )
        conn.commit()
        return cursor.lastrowid


def get_all_feedbacks(teacher_id: int = 1) -> list[dict]:
    """Get all feedbacks for a specific teacher ordered by creation date."""
    with get_db() as conn:
        cursor = conn.execute(
            """
            SELECT id, content, device_id, created_at, included_in_analysis, emotion
            FROM feedbacks
            WHERE teacher_id = ?
            ORDER BY created_at DESC
            """,
            (teacher_id,)
        )
        return [dict(row) for row in cursor.fetchall()]


def get_feedback_by_id(feedback_id: int) -> Optional[dict]:
    """Get a single feedback by ID."""
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT id, content, device_id, created_at, included_in_analysis, emotion, teacher_id FROM feedbacks WHERE id = ?",
            (feedback_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def toggle_feedback_inclusion(feedback_id: int) -> bool:
    """Toggle the included_in_analysis status of a feedback."""
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE feedbacks SET included_in_analysis = NOT included_in_analysis WHERE id = ?",
            (feedback_id,)
        )
        conn.commit()
        return cursor.rowcount > 0


def get_feedbacks_by_ids(feedback_ids: list[int]) -> list[dict]:
    """Get multiple feedbacks by their IDs."""
    if not feedback_ids:
        return []
    with get_db() as conn:
        placeholders = ','.join('?' * len(feedback_ids))
        cursor = conn.execute(
            f"SELECT id, content, device_id, created_at, included_in_analysis, emotion, teacher_id FROM feedbacks WHERE id IN ({placeholders})",
            feedback_ids
        )
        return [dict(row) for row in cursor.fetchall()]


def check_device_limit(device_id: str) -> tuple[bool, int]:
    """
    Check if a device has already submitted a feedback.
    Returns (can_submit, feedback_count)
    """
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT feedback_count FROM device_limits WHERE device_id = ?",
            (device_id,)
        )
        row = cursor.fetchone()
        if row:
            count = row["feedback_count"]
            return (count == 0, count)
        return (True, 0)


def increment_device_feedback(device_id: str):
    """Increment feedback count for a device."""
    with get_db() as conn:
        conn.execute("""
            INSERT INTO device_limits (device_id, feedback_count, last_feedback)
            VALUES (?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(device_id) DO UPDATE SET
                feedback_count = feedback_count + 1,
                last_feedback = CURRENT_TIMESTAMP
        """, (device_id,))
        conn.commit()


def reset_database():
    """Reset the database: delete all feedbacks and device limits."""
    with get_db() as conn:
        conn.execute("DELETE FROM feedbacks")
        conn.execute("DELETE FROM device_limits")
        conn.commit()


def get_feedback_stats(teacher_id: int = 1) -> dict:
    """Get statistics about feedbacks for a specific teacher."""
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN included_in_analysis = 1 THEN 1 ELSE 0 END) as selected
            FROM feedbacks
            WHERE teacher_id = ?
        """, (teacher_id,))
        row = cursor.fetchone()
        return {
            "total": row["total"] or 0,
            "selected": row["selected"] or 0
        }


def import_feedbacks(feedbacks_data: list[dict]) -> int:
    """
    Import multiple feedbacks from exported data.
    Returns the number of feedbacks imported.
    """
    if not feedbacks_data:
        return 0
    
    imported_count = 0
    with get_db() as conn:
        for fb in feedbacks_data:
            device_id = fb.get('device_id') or str(uuid.uuid4())
            created_at = fb.get('created_at')
            emotion = fb.get('emotion')
            included = 1 if fb.get('included_in_analysis') else 0
            teacher_id = fb.get('teacher_id', 1)  # Default to admin if missing, though main.py injects it
            
            if created_at:
                conn.execute(
                    """INSERT INTO feedbacks (content, device_id, created_at, included_in_analysis, emotion, teacher_id)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (fb['content'], device_id, created_at, included, emotion, teacher_id)
                )
            else:
                conn.execute(
                    """INSERT INTO feedbacks (content, device_id, included_in_analysis, emotion, teacher_id)
                       VALUES (?, ?, ?, ?, ?)""",
                    (fb['content'], device_id, included, emotion, teacher_id)
                )
            imported_count += 1
        conn.commit()
    return imported_count


def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get a setting value by key."""
    with get_db() as conn:
        cursor = conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str):
    """Set a setting value by key."""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?",
            (key, value, value)
        )
        conn.commit()


# Teacher Management

def create_teacher(name: str, email: str, password_hash: str, unique_code: str, is_admin: bool = False) -> int:
    """Create a new teacher."""
    with get_db() as conn:
        try:
            cursor = conn.execute(
                """INSERT INTO teachers (name, email, password_hash, unique_code, is_admin) 
                   VALUES (?, ?, ?, ?, ?)""",
                (name, email, password_hash, unique_code, is_admin)
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

def update_teacher_password(email: str, password_hash: str) -> bool:
    """Update teacher's password hash."""
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE teachers SET password_hash = ? WHERE email = ?",
            (password_hash, email)
        )
        conn.commit()
        return cursor.rowcount > 0

def get_teacher_by_email(email: str) -> Optional[dict]:
    """Get teacher by email."""
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM teachers WHERE email = ?", (email,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_teacher_by_id(teacher_id: int) -> Optional[dict]:
    """Get teacher by ID."""
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM teachers WHERE id = ?", (teacher_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_teacher_by_code(unique_code: str) -> Optional[dict]:
    """Get teacher by unique code."""
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM teachers WHERE unique_code = ?", (unique_code,))
        row = cursor.fetchone()
        return dict(row) if row else None

def update_teacher_code(teacher_id: int, new_code: str) -> bool:
    """Update teacher's unique code. Returns True if successful."""
    with get_db() as conn:
        try:
            cursor = conn.execute(
                "UPDATE teachers SET unique_code = ? WHERE id = ?",
                (new_code.upper(), teacher_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.IntegrityError:
            return False

def deduct_credit(teacher_id: int) -> bool:
    """Deduct 1 credit from teacher. Returns True if successful."""
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE teachers SET credits = credits - 1 WHERE id = ? AND credits > 0",
            (teacher_id,)
        )
        conn.commit()
        return cursor.rowcount > 0

def add_credits(teacher_id: int, amount: int):
    """Add credits to teacher."""
    with get_db() as conn:
        conn.execute(
            "UPDATE teachers SET credits = credits + ? WHERE id = ?",
            (amount, teacher_id)
        )
        conn.commit()


def create_payment_receipt(teacher_id: int, file_path: str) -> int:
    """Create a new payment receipt."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO payment_receipts (teacher_id, file_path) VALUES (?, ?)",
            (teacher_id, file_path)
        )
        conn.commit()
        return cursor.lastrowid


def get_all_receipts() -> list[dict]:
    """Get all receipts with teacher details."""
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT r.*, t.name as teacher_name, t.email as teacher_email 
            FROM payment_receipts r
            JOIN teachers t ON r.teacher_id = t.id
            ORDER BY r.created_at DESC
        """)
        return [dict(row) for row in cursor.fetchall()]


def update_receipt_status(receipt_id: int, status: str) -> bool:
    """Update receipt status."""
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE payment_receipts SET status = ? WHERE id = ?",
            (status, receipt_id)
        )
        conn.commit()
        return cursor.rowcount > 0


def get_receipt_by_id(receipt_id: int) -> Optional[dict]:
    """Get receipt by ID."""
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM payment_receipts WHERE id = ?", (receipt_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_teachers() -> list[dict]:
    """Get all teachers."""
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM teachers ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]


def save_analysis(teacher_id: int, summary: str, wordcloud_image: str, feedback_count: int, context: str) -> int:
    """Save an analysis to history."""
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO analysis_history (teacher_id, summary, wordcloud_image, feedback_count, context)
               VALUES (?, ?, ?, ?, ?)""",
            (teacher_id, summary, wordcloud_image, feedback_count, context)
        )
        conn.commit()
        return cursor.lastrowid


def get_analysis_history(teacher_id: int, limit: int = 20) -> list[dict]:
    """Get analysis history for a teacher."""
    with get_db() as conn:
        cursor = conn.execute(
            """SELECT id, summary, wordcloud_image, feedback_count, context, created_at
               FROM analysis_history
               WHERE teacher_id = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (teacher_id, limit)
        )
        return [dict(row) for row in cursor.fetchall()]


def delete_analysis_by_id(analysis_id: int, teacher_id: int) -> bool:
    """Delete an analysis by ID, only if it belongs to the teacher."""
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM analysis_history WHERE id = ? AND teacher_id = ?",
            (analysis_id, teacher_id)
        )
        conn.commit()
        return cursor.rowcount > 0

