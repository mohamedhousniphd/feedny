import time
import sqlite3
from app.database import init_db, get_db, insert_feedback, create_teacher, get_all_feedbacks

# Clean the database before tests
with get_db() as conn:
    conn.execute("DELETE FROM feedbacks")
    conn.execute("DELETE FROM teachers")
    conn.execute("COMMIT")

# Create a teacher
teacher_id = create_teacher("Test Teacher", "test@test.com", "hash", "CODE123")

# Insert 10,000 feedbacks
print("Inserting feedbacks...")
with get_db() as conn:
    conn.execute("BEGIN TRANSACTION")
    for i in range(10000):
        conn.execute(
            "INSERT INTO feedbacks (content, device_id, emotion, teacher_id) VALUES (?, ?, ?, ?)",
            (f"Feedback {i}", f"dev_{i}", "happy", teacher_id)
        )
    conn.execute("COMMIT")

# Get some random feedback IDs to select
with get_db() as conn:
    cursor = conn.execute("SELECT id FROM feedbacks WHERE teacher_id = ? LIMIT 500", (teacher_id,))
    feedback_ids_to_select = [row['id'] for row in cursor.fetchall()]

def unoptimized_approach():
    start = time.time()
    all_feedbacks = get_all_feedbacks(teacher_id)
    # The prompt explicitly mentions:
    # converting feedback_ids to a set instead of list check would be O(1) instead of O(N)
    # So the unoptimized uses a list check:
    selected_feedbacks = [fb for fb in all_feedbacks if fb['id'] in feedback_ids_to_select]
    end = time.time()
    return end - start, len(selected_feedbacks)

def semi_optimized_approach():
    start = time.time()
    all_feedbacks = get_all_feedbacks(teacher_id)
    # Using a set check
    feedback_ids_set = set(feedback_ids_to_select)
    selected_feedbacks = [fb for fb in all_feedbacks if fb['id'] in feedback_ids_set]
    end = time.time()
    return end - start, len(selected_feedbacks)

def fully_optimized_approach():
    start = time.time()
    with get_db() as conn:
        placeholders = ','.join('?' * len(feedback_ids_to_select))
        cursor = conn.execute(
            f"SELECT id, content, device_id, created_at, included_in_analysis, emotion "
            f"FROM feedbacks WHERE teacher_id = ? AND id IN ({placeholders})",
            [teacher_id] + feedback_ids_to_select
        )
        selected_feedbacks = [dict(row) for row in cursor.fetchall()]
    end = time.time()
    return end - start, len(selected_feedbacks)

print("Running unoptimized...")
t1, c1 = unoptimized_approach()

print("Running semi-optimized (set)...")
t2, c2 = semi_optimized_approach()

print("Running fully optimized (SQLite)...")
t3, c3 = fully_optimized_approach()

print(f"Unoptimized time: {t1:.4f}s (count: {c1})")
print(f"Semi-optimized time: {t2:.4f}s (count: {c2})")
print(f"Fully optimized time: {t3:.4f}s (count: {c3})")
print(f"Improvement (Unoptimized vs Fully Optimized): {t1/t3:.2f}x faster")
