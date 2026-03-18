import time
import sqlite3
import random
from app.database import init_db, get_db, insert_feedback, create_teacher, get_all_feedbacks

# Clean the database before tests
def setup_data():
    init_db()
    with get_db() as conn:
        conn.execute("DELETE FROM feedbacks")
        conn.execute("DELETE FROM teachers")
        conn.commit()

# Create a teacher and feedbacks
setup_data()
teacher_id = create_teacher("Test Teacher", "test@test.com", "hash", "CODE123")

print("Inserting 10,000 feedbacks...")
with get_db() as conn:
    for i in range(10000):
        # Use emotion as integer if required by schema, or string if supported
        conn.execute(
            "INSERT INTO feedbacks (content, device_id, emotion, teacher_id) VALUES (?, ?, ?, ?)",
            (f"Feedback {i}", f"dev_{i}", 1, teacher_id)
        )
    conn.commit()

# Get some random feedback IDs to select
with get_db() as conn:
    cursor = conn.execute("SELECT id FROM feedbacks WHERE teacher_id = ? LIMIT 500", (teacher_id,))
    feedback_ids_to_select = [row['id'] for row in cursor.fetchall()]

def unoptimized_approach():
    start = time.perf_counter()
    all_feedbacks = get_all_feedbacks(teacher_id)
    selected_feedbacks = [fb for fb in all_feedbacks if fb['id'] in feedback_ids_to_select]
    end = time.perf_counter()
    return end - start, len(selected_feedbacks)

def semi_optimized_approach():
    start = time.perf_counter()
    all_feedbacks = get_all_feedbacks(teacher_id)
    feedback_ids_set = set(feedback_ids_to_select)
    selected_feedbacks = [fb for fb in all_feedbacks if fb['id'] in feedback_ids_set]
    end = time.perf_counter()
    return end - start, len(selected_feedbacks)

def fully_optimized_approach():
    start = time.perf_counter()
    from app.database import get_feedbacks_by_ids_and_teacher
    selected_feedbacks = get_feedbacks_by_ids_and_teacher(feedback_ids_to_select, teacher_id)
    end = time.perf_counter()
    return end - start, len(selected_feedbacks)

if __name__ == "__main__":
    print("Running unoptimized...")
    t1, c1 = unoptimized_approach()
    
    print("Running semi-optimized (set)...")
    t2, c2 = semi_optimized_approach()
    
    print("Running fully optimized (SQLite)...")
    t3, c3 = fully_optimized_approach()
    
    print(f"Unoptimized time: {t1:.6f}s (count: {c1})")
    print(f"Semi-optimized time: {t2:.6f}s (count: {c2})")
    print(f"Fully optimized time: {t3:.6f}s (count: {c3})")
    print(f"Improvement (Unoptimized vs Fully Optimized): {t1/t3:.2f}x faster")
