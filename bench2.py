import sqlite3
import time

def setup_db():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('CREATE TABLE feedbacks (id INTEGER PRIMARY KEY, teacher_id INTEGER, content TEXT, device_id TEXT, created_at TEXT, included_in_analysis INTEGER, emotion TEXT)')

    # insert 10000 records
    records = [(i, 1, f"content {i}", "dev", "2023-10-01", 1, "happy") for i in range(10000)]
    conn.executemany('INSERT INTO feedbacks (id, teacher_id, content, device_id, created_at, included_in_analysis, emotion) VALUES (?, ?, ?, ?, ?, ?, ?)', records)
    return conn

conn = setup_db()

def get_feedbacks_by_ids(feedback_ids: list[int]) -> list[dict]:
    if not feedback_ids:
        return []
    placeholders = ','.join('?' * len(feedback_ids))
    cursor = conn.execute(
        f"SELECT id, content, device_id, created_at, included_in_analysis, emotion, teacher_id FROM feedbacks WHERE id IN ({placeholders})",
        feedback_ids
    )
    return [dict(row) for row in cursor.fetchall()]

def get_all_feedbacks(teacher_id: int) -> list[dict]:
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

def run():
    teacher_id = 1
    feedbacks_str = ",".join(str(i) for i in range(0, 10000, 2))

    start = time.time()
    for _ in range(10):
        # original
        feedback_ids = [int(id.strip()) for id in feedbacks_str.split(",") if id.strip()]
        all_feedbacks = get_all_feedbacks(teacher_id)
        selected_feedbacks = [fb for fb in all_feedbacks if fb['id'] in feedback_ids]
    print(f"Original: {time.time() - start:.4f}s")

    start = time.time()
    for _ in range(10):
        # list optimized
        feedback_ids = [int(id.strip()) for id in feedbacks_str.split(",") if id.strip()]
        selected_feedbacks = get_feedbacks_by_ids(feedback_ids)
        feedbacks_data = [fb for fb in selected_feedbacks if fb.get('teacher_id') == teacher_id]
    print(f"SQL IN optimized: {time.time() - start:.4f}s")

    start = time.time()
    for _ in range(10):
        # set optimized
        feedback_ids = set([int(id.strip()) for id in feedbacks_str.split(",") if id.strip()])
        all_feedbacks = get_all_feedbacks(teacher_id)
        selected_feedbacks = [fb for fb in all_feedbacks if fb['id'] in feedback_ids]
    print(f"Set optimized: {time.time() - start:.4f}s")

run()
