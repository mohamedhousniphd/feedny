import time
import random
from app.database import get_db, init_db

# Setup
def setup_data():
    init_db()
    with get_db() as conn:
        conn.execute("DELETE FROM feedbacks")
        conn.commit()

        # Insert 10,000 feedbacks for teacher 1
        for i in range(10000):
            conn.execute("INSERT INTO feedbacks (content, device_id, emotion, teacher_id) VALUES (?, ?, ?, ?)",
                         (f"Feedback {i}", "device1", 1, 1))
        conn.commit()

# Measure Suboptimal (Baseline from prompt)
def suboptimal_fetch(teacher_id, feedback_ids):
    from app.database import get_all_feedbacks
    all_feedbacks = get_all_feedbacks(teacher_id)
    # List check O(N)
    selected = [fb for fb in all_feedbacks if fb['id'] in feedback_ids]
    return selected

# Measure Optimal
def optimal_fetch(teacher_id, feedback_ids):
    from app.database import get_db
    if not feedback_ids:
        return []
    with get_db() as conn:
        placeholders = ','.join('?' * len(feedback_ids))
        cursor = conn.execute(
            f"SELECT id, content, device_id, created_at, included_in_analysis, emotion, teacher_id "
            f"FROM feedbacks WHERE teacher_id = ? AND id IN ({placeholders})",
            [teacher_id] + feedback_ids
        )
        return [dict(row) for row in cursor.fetchall()]

def run_benchmark():
    print("Setting up data...")
    setup_data()

    # We want to select 100 random feedbacks out of 10,000
    with get_db() as conn:
        cursor = conn.execute("SELECT id FROM feedbacks WHERE teacher_id = 1")
        all_ids = [row[0] for row in cursor.fetchall()]

    target_ids = random.sample(all_ids, 100)

    # Warmup
    _ = suboptimal_fetch(1, target_ids)
    _ = optimal_fetch(1, target_ids)

    # Multiple runs
    iterations = 50

    print("Running baseline (Suboptimal O(N) filtering)...")
    start = time.perf_counter()
    for _ in range(iterations):
        res1 = suboptimal_fetch(1, target_ids)
    end = time.perf_counter()
    t_suboptimal = (end - start) / iterations
    print(f"Baseline Avg Time: {t_suboptimal:.6f}s")

    print("Running optimized (SQLite query)...")
    start = time.perf_counter()
    for _ in range(iterations):
        res2 = optimal_fetch(1, target_ids)
    end = time.perf_counter()
    t_optimal = (end - start) / iterations
    print(f"Optimized Avg Time: {t_optimal:.6f}s")

    print(f"Improvement: {t_suboptimal / t_optimal:.2f}x faster")

if __name__ == "__main__":
    run_benchmark()
