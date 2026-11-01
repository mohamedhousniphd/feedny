import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional
import uuid


DEFAULT_DB_PATH = "feedny.db"


def resolve_db_path() -> str:
    """Resolve the SQLite file path.

    Priority: DB_PATH > DATABASE_URL > DEFAULT_DB_PATH.

    On Railway the database must live on a mounted volume (e.g. /app/data)
    so that data survives redeploys and restarts.
    """
    raw = os.getenv("DB_PATH") or os.getenv("DATABASE_URL") or DEFAULT_DB_PATH
    raw = raw.strip()
    if raw.startswith("sqlite:///"):
        raw = raw[len("sqlite:///"):]
    elif raw.startswith("sqlite://"):
        raw = raw[len("sqlite://"):]
    return raw or DEFAULT_DB_PATH


DATABASE_URL = resolve_db_path()

# Make sure the parent directory exists (e.g. a mounted volume at /app/data).
try:
    _db_dir = os.path.dirname(os.path.abspath(DATABASE_URL))
    if _db_dir:
        os.makedirs(_db_dir, exist_ok=True)
except OSError:
    pass


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
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        with open(schema_path, 'r') as f:
            conn.executescript(f.read())
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

        _migrate_client_events(conn)
        _migrate_analysis_history(conn)


CLIENT_EVENT_COLUMNS = {
    "first_input_seconds": "REAL",
    "typing_seconds": "REAL",
    "total_seconds": "REAL",
    "keystrokes": "INTEGER",
    "backspaces": "INTEGER",
    "pasted": "BOOLEAN",
    "paste_chars": "INTEGER",
    "idle_seconds": "REAL",
    "network_type": "TEXT",
    "ttfb_ms": "REAL",
    "dom_ready_ms": "REAL",
    "load_ms": "REAL",
    "first_paint_ms": "REAL",
    "lcp_ms": "REAL",
    "page_seconds": "REAL",
    "left_without_submit": "BOOLEAN",
    "prefers_dark": "BOOLEAN",
    "reduced_motion": "BOOLEAN",
    "high_contrast": "BOOLEAN",
    "pointer_type": "TEXT",
    "hover_capable": "BOOLEAN",
    "dpr": "REAL",
    "orientation": "TEXT",
}


def _migrate_analysis_history(conn):
    """Add the anonymous technical snapshot column to analysis history."""
    try:
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(analysis_history)")}
    except sqlite3.Error:
        return
    if "technical_context" not in existing:
        conn.execute("ALTER TABLE analysis_history ADD COLUMN technical_context TEXT")
        conn.commit()


def _migrate_client_events(conn):
    """Add timing columns to client_events on existing databases."""
    try:
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(client_events)")}
    except sqlite3.Error:
        return
    for column, column_type in CLIENT_EVENT_COLUMNS.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE client_events ADD COLUMN {column} {column_type}")
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


def get_feedbacks_with_context(teacher_id: int = 1) -> list[dict]:
    """Feedbacks + the anonymous technical context of their device.

    Prefers the "submit" event (captured with the feedback) and falls back to
    the "join" event of the same device.
    """
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT
                f.id, f.content, f.device_id, f.created_at,
                f.included_in_analysis, f.emotion,
                COALESCE(es.device_type, ej.device_type)       AS device_type,
                COALESCE(es.browser, ej.browser)               AS browser,
                COALESCE(es.os, ej.os)                         AS os,
                COALESCE(es.connection_type, ej.connection_type) AS connection_type,
                COALESCE(es.network_type, ej.network_type)     AS network_type,
                COALESCE(es.downlink, ej.downlink)             AS downlink,
                COALESCE(es.rtt, ej.rtt)                       AS rtt,
                COALESCE(es.country, ej.country)               AS country,
                COALESCE(es.language, ej.language)             AS language,
                COALESCE(es.typing_seconds, ej.typing_seconds) AS typing_seconds,
                COALESCE(es.first_input_seconds, ej.first_input_seconds) AS first_input_seconds,
                COALESCE(es.total_seconds, ej.total_seconds)   AS total_seconds,
                COALESCE(es.keystrokes, ej.keystrokes)         AS keystrokes,
                COALESCE(es.pasted, ej.pasted)                 AS pasted
            FROM feedbacks f
            LEFT JOIN client_events es ON es.id = (
                SELECT id FROM client_events
                WHERE device_id = f.device_id AND teacher_id = f.teacher_id AND event = 'submit'
                ORDER BY id DESC LIMIT 1
            )
            LEFT JOIN client_events ej ON ej.id = (
                SELECT id FROM client_events
                WHERE device_id = f.device_id AND teacher_id = f.teacher_id AND event = 'join'
                ORDER BY id DESC LIMIT 1
            )
            WHERE f.teacher_id = ?
            ORDER BY f.created_at DESC
            """,
            (teacher_id,),
        )
        return [dict(row) for row in rows]


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


def get_feedbacks_by_ids_and_teacher(feedback_ids: list[int], teacher_id: int) -> list[dict]:
    """Get multiple feedbacks by their IDs for a specific teacher."""
    if not feedback_ids:
        return []
    with get_db() as conn:
        placeholders = ','.join('?' * len(feedback_ids))
        query = f"""
            SELECT id, content, device_id, created_at, included_in_analysis, emotion, teacher_id
            FROM feedbacks
            WHERE teacher_id = ? AND id IN ({placeholders})
            ORDER BY created_at DESC
        """
        params = [teacher_id] + feedback_ids
        cursor = conn.execute(query, params)
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


def _backup_root() -> str:
    """Directory where DB snapshots are stored (default: next to the DB file)."""
    return os.getenv("BACKUP_DIR") or os.path.join(
        os.path.dirname(os.path.abspath(DATABASE_URL)), "backups"
    )


def _backup_keep() -> int:
    try:
        return max(1, int(os.getenv("BACKUP_KEEP", "10")))
    except ValueError:
        return 10


def create_db_backup(label: Optional[str] = None) -> dict:
    """Create a consistent snapshot of the SQLite database.

    Uses sqlite3's online backup API, so it is safe while the app is running
    (it also captures the WAL content).
    """
    backup_dir = _backup_root()
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now()
    suffix = f"-{label}" if label else ""
    name = f"feedny-{timestamp.strftime('%Y%m%d-%H%M%S')}{suffix}.db"
    dest = os.path.join(backup_dir, name)

    with sqlite3.connect(DATABASE_URL) as source:
        with sqlite3.connect(dest) as target:
            source.backup(target)

    prune_db_backups()
    return {
        "name": name,
        "path": dest,
        "size": os.path.getsize(dest),
        "created_at": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
    }


def list_db_backups() -> list[dict]:
    """List available DB snapshots, newest first."""
    backup_dir = _backup_root()
    if not os.path.isdir(backup_dir):
        return []

    backups = []
    for filename in os.listdir(backup_dir):
        if not (filename.startswith("feedny-") and filename.endswith(".db")):
            continue
        path = os.path.join(backup_dir, filename)
        try:
            stat = os.stat(path)
        except OSError:
            continue
        backups.append({
            "name": filename,
            "size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        })
    backups.sort(key=lambda item: item["created_at"], reverse=True)
    return backups


def prune_db_backups(keep: Optional[int] = None) -> int:
    """Delete oldest snapshots, keeping the most recent `keep` ones."""
    keep = keep if keep is not None else _backup_keep()
    backups = list_db_backups()
    removed = 0
    for backup in backups[keep:]:
        try:
            os.remove(os.path.join(_backup_root(), backup["name"]))
            removed += 1
        except OSError:
            continue
    return removed


def maybe_backup_daily() -> Optional[dict]:
    """Create at most one automatic snapshot per day (called on startup)."""
    today = datetime.now().strftime("%Y%m%d")
    for backup in list_db_backups():
        if backup["name"].startswith(f"feedny-{today}-") and "auto" in backup["name"]:
            return None
    return create_db_backup("auto")


def reset_database(teacher_id: Optional[int] = None):
    """Reset the database: delete all feedbacks and device limits, or optionally filter by teacher_id."""
    with get_db() as conn:
        if teacher_id is not None:
            conn.execute("DELETE FROM device_limits WHERE device_id IN (SELECT device_id FROM feedbacks WHERE teacher_id = ?)", (teacher_id,))
            conn.execute("DELETE FROM feedbacks WHERE teacher_id = ?", (teacher_id,))
            conn.execute("DELETE FROM client_events WHERE teacher_id = ?", (teacher_id,))
        else:
            conn.execute("DELETE FROM feedbacks")
            conn.execute("DELETE FROM device_limits")
            conn.execute("DELETE FROM client_events")
        conn.commit()


def recent_join_exists(teacher_id: Optional[int], device_id: Optional[str], minutes: int = 15) -> bool:
    """Avoid flooding client_events when a student reloads the page."""
    if not device_id:
        return False
    with get_db() as conn:
        row = conn.execute(
            """SELECT 1 FROM client_events
               WHERE event = 'join' AND teacher_id = ? AND device_id = ?
                 AND created_at >= datetime('now', ?)
               LIMIT 1""",
            (teacher_id, device_id, f"-{minutes} minutes"),
        ).fetchone()
        return bool(row)


def save_client_event(event: str, teacher_id: Optional[int], device_id: Optional[str], data: dict) -> int:
    """Store one anonymous technical event ('join' or 'submit')."""
    if event == "join" and recent_join_exists(teacher_id, device_id):
        return 0
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO client_events (
                event, teacher_id, device_id, device_type, browser, os, user_agent,
                platform, language, timezone, screen, viewport, connection_type,
                network_type, downlink, rtt, save_data, touch, memory_gb, cores, country,
                referrer, fill_seconds, first_input_seconds, typing_seconds,
                total_seconds, keystrokes, backspaces, pasted, paste_chars, idle_seconds,
                ttfb_ms, dom_ready_ms, load_ms, first_paint_ms, lcp_ms, page_seconds,
                left_without_submit, prefers_dark, reduced_motion, high_contrast,
                pointer_type, hover_capable, dpr, orientation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event, teacher_id, device_id,
                data.get("device_type"), data.get("browser"), data.get("os"),
                data.get("user_agent"), data.get("platform"), data.get("language"),
                data.get("timezone"), data.get("screen"), data.get("viewport"),
                data.get("connection_type"), data.get("network_type"),
                data.get("downlink"), data.get("rtt"),
                data.get("save_data"), data.get("touch"), data.get("memory_gb"),
                data.get("cores"), data.get("country"), data.get("referrer"),
                data.get("fill_seconds"), data.get("first_input_seconds"),
                data.get("typing_seconds"), data.get("total_seconds"),
                data.get("keystrokes"), data.get("backspaces"), data.get("pasted"),
                data.get("paste_chars"), data.get("idle_seconds"),
                data.get("ttfb_ms"), data.get("dom_ready_ms"), data.get("load_ms"),
                data.get("first_paint_ms"), data.get("lcp_ms"), data.get("page_seconds"),
                data.get("left_without_submit"), data.get("prefers_dark"),
                data.get("reduced_motion"), data.get("high_contrast"),
                data.get("pointer_type"), data.get("hover_capable"),
                data.get("dpr"), data.get("orientation"),
            ),
        )
        conn.commit()
        return cursor.lastrowid


def save_client_error(teacher_id: Optional[int], device_id: Optional[str], data: dict) -> int:
    """Store a JS error reported by the browser (anonymous)."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM client_errors WHERE device_id = ? AND created_at >= datetime('now', '-1 hour')",
            (device_id,),
        ).fetchone()
        if row and row[0] >= 10:  # anti-flood
            return 0
        cursor = conn.execute(
            """INSERT INTO client_errors
               (teacher_id, device_id, message, source, line, column_number, stack, url, user_agent)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                teacher_id, device_id,
                (data.get("message") or "")[:500],
                (data.get("source") or "")[:300],
                data.get("line"), data.get("column"),
                (data.get("stack") or "")[:1500],
                (data.get("url") or "")[:300],
                (data.get("user_agent") or "")[:400],
            ),
        )
        conn.commit()
        return cursor.lastrowid


def get_client_errors(teacher_id: Optional[int] = None, limit: int = 10) -> dict:
    """Recent JS errors + total count for the dashboard."""
    where = "WHERE teacher_id = ?" if teacher_id is not None else ""
    params = (teacher_id,) if teacher_id is not None else ()
    with get_db() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM client_errors {where}", params).fetchone()[0]
        rows = conn.execute(
            f"""SELECT message, source, line, created_at
                FROM client_errors {where}
                ORDER BY created_at DESC LIMIT ?""",
            params + (limit,),
        ).fetchall()
        return {"total": total, "recent": [dict(row) for row in rows]}


def _count_by(conn, column: str, teacher_id: Optional[int], event: str = "submit") -> list[dict]:
    if teacher_id is None:
        rows = conn.execute(
            f"""SELECT COALESCE({column}, 'inconnu') AS label, COUNT(*) AS count
                FROM client_events WHERE event = ?
                GROUP BY label ORDER BY count DESC""",
            (event,),
        ).fetchall()
    else:
        rows = conn.execute(
            f"""SELECT COALESCE({column}, 'inconnu') AS label, COUNT(*) AS count
                FROM client_events WHERE event = ? AND teacher_id = ?
                GROUP BY label ORDER BY count DESC""",
            (event, teacher_id),
        ).fetchall()
    return [{"label": row["label"], "count": row["count"]} for row in rows]


def purge_client_events(before: Optional[str] = None, teacher_id: Optional[int] = None) -> int:
    """Delete anonymous telemetry rows (optionally before a YYYY-MM-DD date)."""
    query = "DELETE FROM client_events WHERE 1 = 1"
    params: list = []
    if before:
        query += " AND date(created_at) < date(?)"
        params.append(before)
    if teacher_id is not None:
        query += " AND teacher_id = ?"
        params.append(teacher_id)
    with get_db() as conn:
        cursor = conn.execute(query, params)
        conn.commit()
        return cursor.rowcount


def get_technical_insights(teacher_id: Optional[int] = None) -> dict:
    """Aggregate anonymous technical context for the dashboard."""
    where = "event = ? AND teacher_id = ?" if teacher_id is not None else "event = ?"
    join_where = "event = ? AND teacher_id = ?" if teacher_id is not None else "event = ?"
    base_params = (teacher_id,) if teacher_id is not None else ()

    with get_db() as conn:
        joins = conn.execute(
            f"SELECT COUNT(DISTINCT COALESCE(device_id, id)) FROM client_events WHERE {join_where}",
            ("join",) + base_params,
        ).fetchone()[0]
        # Real feedbacks in the DB (telemetry submits can double-count retries)
        if teacher_id is None:
            submits = conn.execute("SELECT COUNT(*) FROM feedbacks").fetchone()[0]
        else:
            submits = conn.execute(
                "SELECT COUNT(*) FROM feedbacks WHERE teacher_id = ?", (teacher_id,)
            ).fetchone()[0]

        timing = conn.execute(
            f"""SELECT AVG(fill_seconds) AS avg_fill,
                       AVG(first_input_seconds) AS avg_first_input,
                       AVG(typing_seconds) AS avg_typing,
                       AVG(total_seconds) AS avg_total,
                       AVG(idle_seconds) AS avg_idle,
                       AVG(keystrokes) AS avg_keystrokes,
                       AVG(backspaces) AS avg_backspaces,
                       SUM(CASE WHEN pasted = 1 THEN 1 ELSE 0 END) AS pasted,
                       COUNT(fill_seconds) AS timed
                FROM client_events WHERE {where}""",
            ("submit",) + base_params,
        ).fetchone()
        latency = conn.execute(
            f"""SELECT AVG(rtt) AS avg_rtt,
                       AVG(downlink) AS avg_downlink,
                       SUM(CASE WHEN downlink >= 10 AND rtt < 80 THEN 1 ELSE 0 END) AS fast,
                       COUNT(CASE WHEN downlink IS NOT NULL AND rtt IS NOT NULL THEN 1 END) AS measured
                FROM client_events WHERE {where}""",
            ("submit",) + base_params,
        ).fetchone()
        slow_share = conn.execute(
            f"""SELECT
                    SUM(CASE WHEN connection_type IN ('slow-2g','2g','3g') THEN 1 ELSE 0 END) AS slow,
                    COUNT(*) AS total
                FROM client_events WHERE {where} AND connection_type IS NOT NULL""",
            ("submit",) + base_params,
        ).fetchone()
        dates = conn.execute(
            f"""SELECT MIN(created_at) AS first_seen, MAX(created_at) AS last_seen
                FROM client_events WHERE {join_where}""",
            ("join",) + base_params,
        ).fetchone()

        emotion_stats = conn.execute(
            """SELECT AVG(emotion) AS avg_emotion, COUNT(emotion) AS responses
               FROM feedbacks WHERE teacher_id = ? AND emotion IS NOT NULL""",
            (teacher_id,),
        ).fetchone()
        emotion_counts = conn.execute(
            """SELECT emotion AS label, COUNT(*) AS count
               FROM feedbacks WHERE teacher_id = ? AND emotion IS NOT NULL
               GROUP BY emotion ORDER BY emotion""",
            (teacher_id,),
        ).fetchall()

        perf = conn.execute(
            f"""SELECT AVG(load_ms) AS avg_load, AVG(ttfb_ms) AS avg_ttfb,
                       AVG(first_paint_ms) AS avg_fp, AVG(lcp_ms) AS avg_lcp,
                       AVG(page_seconds) AS avg_page,
                       SUM(CASE WHEN prefers_dark = 1 THEN 1 ELSE 0 END) AS dark,
                       SUM(CASE WHEN reduced_motion = 1 THEN 1 ELSE 0 END) AS reduced,
                       COUNT(*) AS total
                FROM client_events WHERE {join_where}""",
            ("submit",) + base_params,
        ).fetchone()

        leaves = conn.execute(
            f"""SELECT COUNT(DISTINCT COALESCE(device_id, id)) AS leaves,
                       AVG(page_seconds) AS avg_left_seconds
                FROM client_events
                WHERE {join_where} AND left_without_submit = 1""",
            ("leave",) + base_params,
        ).fetchone()

        return {
            "joins": joins,
            "submits": submits,
            "conversion_rate": min(round((submits / joins) * 100, 1), 100.0) if joins else 0.0,
            "avg_fill_seconds": round(timing["avg_fill"], 1) if timing and timing["avg_fill"] else None,
            "avg_first_input_seconds": round(timing["avg_first_input"], 1) if timing and timing["avg_first_input"] else None,
            "avg_typing_seconds": round(timing["avg_typing"], 1) if timing and timing["avg_typing"] else None,
            "avg_total_seconds": round(timing["avg_total"], 1) if timing and timing["avg_total"] else None,
            "avg_idle_seconds": round(timing["avg_idle"], 1) if timing and timing["avg_idle"] else None,
            "avg_keystrokes": round(timing["avg_keystrokes"], 0) if timing and timing["avg_keystrokes"] else None,
            "avg_backspaces": round(timing["avg_backspaces"], 0) if timing and timing["avg_backspaces"] else None,
            "paste_rate": round((timing["pasted"] or 0) / submits * 100, 1) if submits and timing else None,
            "timed_submits": timing["timed"] if timing else 0,
            "avg_rtt_ms": round(latency["avg_rtt"], 0) if latency and latency["avg_rtt"] else None,
            "avg_downlink_mbps": round(latency["avg_downlink"], 1) if latency and latency["avg_downlink"] else None,
            "fast_network_share": round((latency["fast"] or 0) / latency["measured"] * 100, 1) if latency and latency["measured"] else None,
            "slow_network_share": round((slow_share["slow"] or 0) / slow_share["total"] * 100, 1) if slow_share and slow_share["total"] else None,
            "avg_load_ms": round(perf["avg_load"], 0) if perf and perf["avg_load"] else None,
            "avg_ttfb_ms": round(perf["avg_ttfb"], 0) if perf and perf["avg_ttfb"] else None,
            "avg_first_paint_ms": round(perf["avg_fp"], 0) if perf and perf["avg_fp"] else None,
            "avg_lcp_ms": round(perf["avg_lcp"], 0) if perf and perf["avg_lcp"] else None,
            "avg_emotion": round(emotion_stats["avg_emotion"], 2) if emotion_stats and emotion_stats["avg_emotion"] else None,
            "emotion_responses": emotion_stats["responses"] if emotion_stats else 0,
            "emotion_counts": [{"label": row["label"], "count": row["count"]} for row in emotion_counts],
            "abandons": leaves["leaves"] if leaves else 0,
            "avg_abandon_seconds": round(leaves["avg_left_seconds"], 0) if leaves and leaves["avg_left_seconds"] else None,
            "dark_share": round((perf["dark"] or 0) / perf["total"] * 100, 1) if perf and perf["total"] else None,
            "reduced_motion_share": round((perf["reduced"] or 0) / perf["total"] * 100, 1) if perf and perf["total"] else None,
            "first_seen": dates["first_seen"] if dates else None,
            "last_seen": dates["last_seen"] if dates else None,
            "device_types": _count_by(conn, "device_type", teacher_id),
            "browsers": _count_by(conn, "browser", teacher_id),
            "os": _count_by(conn, "os", teacher_id),
            "connection_types": _count_by(conn, "connection_type", teacher_id),
            "countries": _count_by(conn, "country", teacher_id),
            "screens": _count_by(conn, "viewport", teacher_id),
            "network_types": _count_by(conn, "network_type", teacher_id),
        }


def get_feedback_stats(teacher_id: int = 1) -> dict:
    """Get statistics about feedbacks for a specific teacher."""
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN included_in_analysis = 1 THEN 1 ELSE 0 END) as selected,
                AVG(emotion) as avg_emotion,
                COUNT(emotion) as emotion_responses
            FROM feedbacks
            WHERE teacher_id = ?
        """, (teacher_id,))
        row = cursor.fetchone()
        return {
            "total": row["total"] or 0,
            "selected": row["selected"] or 0,
            "avg_emotion": round(row["avg_emotion"], 2) if row["avg_emotion"] else None,
            "emotion_responses": row["emotion_responses"] or 0,
        }


def import_feedbacks(feedbacks_data: list[dict]) -> int:
    """
    Import multiple feedbacks from exported data.
    Returns the number of feedbacks imported.
    """
    if not feedbacks_data:
        return 0
    
    with_created_at = []
    without_created_at = []

    for fb in feedbacks_data:
        if not isinstance(fb, dict) or not isinstance(fb.get('content'), str):
            continue
        content = fb['content'].strip()
        if not content or len(content) > 2000:
            continue
        fb['content'] = content
        device_id = fb.get('device_id') or str(uuid.uuid4())
        created_at = fb.get('created_at')
        emotion = fb.get('emotion')
        included = 1 if fb.get('included_in_analysis') else 0
        teacher_id = fb.get('teacher_id', 1)  # Default to admin if missing, though main.py injects it

        if created_at:
            with_created_at.append((fb['content'], device_id, created_at, included, emotion, teacher_id))
        else:
            without_created_at.append((fb['content'], device_id, included, emotion, teacher_id))
            
    with get_db() as conn:
        if with_created_at:
            conn.executemany(
                """INSERT INTO feedbacks (content, device_id, created_at, included_in_analysis, emotion, teacher_id)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                with_created_at
            )
        if without_created_at:
            conn.executemany(
                """INSERT INTO feedbacks (content, device_id, included_in_analysis, emotion, teacher_id)
                   VALUES (?, ?, ?, ?, ?)""",
                without_created_at
            )
        conn.commit()
    return len(feedbacks_data)


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


def save_analysis(teacher_id: int, summary: str, wordcloud_image: str, feedback_count: int, context: str,
                  technical_context: Optional[str] = None) -> int:
    """Save an analysis to history (with the anonymous technical snapshot)."""
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO analysis_history
               (teacher_id, summary, wordcloud_image, feedback_count, context, technical_context)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (teacher_id, summary, wordcloud_image, feedback_count, context, technical_context)
        )
        conn.commit()
        return cursor.lastrowid


def get_analysis_history(teacher_id: int, limit: int = 20) -> list[dict]:
    """Get analysis history for a teacher."""
    with get_db() as conn:
        cursor = conn.execute(
            """SELECT id, summary, wordcloud_image, feedback_count, context, technical_context, created_at
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

