import sqlite3

conn = sqlite3.connect("validation.db")
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM tts_progress WHERE status='complete'")
count = cursor.fetchone()[0]
print(f"Complete chunks: {count}")
conn.close()
