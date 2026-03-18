import sqlite3
import time

def setup_db():
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute('CREATE TABLE feedbacks (id INTEGER PRIMARY KEY, teacher_id INTEGER, content TEXT)')

    # insert 10000 records
    records = [(i, 1, f"content {i}") for i in range(10000)]
    conn.executemany('INSERT INTO feedbacks (id, teacher_id, content) VALUES (?, ?, ?)', records)
    return conn

def bench():
    conn = setup_db()

    selected_ids = list(range(0, 10000, 2))  # 5000 ids

    # Baseline: get all and filter
    start = time.time()
    for _ in range(100):
        cursor = conn.execute('SELECT * FROM feedbacks WHERE teacher_id = ?', (1,))
        all_fb = [dict(row) for row in cursor.fetchall()]
        selected = [fb for fb in all_fb if fb['id'] in selected_ids]
    print(f"List filter: {time.time() - start:.4f}s")

    # Baseline with set
    start = time.time()
    for _ in range(100):
        selected_set = set(selected_ids)
        cursor = conn.execute('SELECT * FROM feedbacks WHERE teacher_id = ?', (1,))
        all_fb = [dict(row) for row in cursor.fetchall()]
        selected = [fb for fb in all_fb if fb['id'] in selected_set]
    print(f"Set filter: {time.time() - start:.4f}s")

    # Optimized: SQL IN
    start = time.time()
    for _ in range(100):
        placeholders = ','.join('?' * len(selected_ids))
        cursor = conn.execute(f'SELECT * FROM feedbacks WHERE teacher_id = ? AND id IN ({placeholders})', [1] + selected_ids)
        selected = [dict(row) for row in cursor.fetchall()]
    print(f"SQL IN filter: {time.time() - start:.4f}s")

bench()
