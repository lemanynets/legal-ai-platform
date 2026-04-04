import sqlite3
import os

db_path = r'c:\Users\ja\Documents\legal-ai-platform\dev.db'

if not os.path.exists(db_path):
    print(f"Error: Database not found at {db_path}")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # List all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [table[0] for table in cursor.fetchall()]
    print(f"Tables in database: {tables}")
    
    conn.close()
except Exception as e:
    print(f"Error: {e}")
    exit(1)
