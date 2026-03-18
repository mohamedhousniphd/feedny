import time
import uuid
import sqlite3
from app.database import import_feedbacks, init_db, get_db

# Setup
init_db()

# Generate large amount of test data
test_data = []
for i in range(100000):
    test_data.append({
        'content': f'Test feedback {i}',
        'device_id': str(uuid.uuid4()),
        'created_at': '2023-10-27 10:00:00',
        'included_in_analysis': True,
        'emotion': 'happy',
        'teacher_id': 1
    })

# Measure
start_time = time.time()
import_feedbacks(test_data)
end_time = time.time()

print(f"Time taken for 100000 feedbacks: {end_time - start_time:.4f} seconds")

# Cleanup
with get_db() as conn:
    conn.execute("DELETE FROM feedbacks")
    conn.commit()
