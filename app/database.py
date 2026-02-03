import sqlite3
from contextlib import contextmanager
from typing import Optional
from datetime import datetime


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
    """Initialize the database with required tables."""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedbacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                device_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                included_in_analysis BOOLEAN DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS device_limits (
                device_id TEXT PRIMARY KEY,
                feedback_count INTEGER DEFAULT 0,
                last_feedback TIMESTAMP
            )
        """)
        conn.commit()


def insert_feedback(content: str, device_id: str) -> int:
    """Insert a new feedback and return its ID."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO feedbacks (content, device_id) VALUES (?, ?)",
            (content, device_id)
        )
        conn.commit()
        return cursor.lastrowid


def get_all_feedbacks() -> list[dict]:
    """Get all feedbacks ordered by creation date (newest first)."""
    with get_db() as conn:
        cursor = conn.execute(
            """
            SELECT id, content, device_id, created_at, included_in_analysis
            FROM feedbacks
            ORDER BY created_at DESC
            """
        )
        return [dict(row) for row in cursor.fetchall()]


def get_feedback_by_id(feedback_id: int) -> Optional[dict]:
    """Get a single feedback by ID."""
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT id, content, device_id, created_at, included_in_analysis FROM feedbacks WHERE id = ?",
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
            f"SELECT id, content, device_id, created_at, included_in_analysis FROM feedbacks WHERE id IN ({placeholders})",
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


def get_feedback_stats() -> dict:
    """Get statistics about feedbacks."""
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN included_in_analysis = 1 THEN 1 ELSE 0 END) as selected
            FROM feedbacks
        """)
        row = cursor.fetchone()
        return {
            "total": row["total"] or 0,
            "selected": row["selected"] or 0
        }
