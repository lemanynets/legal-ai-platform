import sqlite3
import os

db_path = r'c:\Users\ja\Documents\legal-ai-platform\dev.db'

if not os.path.exists(db_path):
    print(f"Error: Database not found at {db_path}")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if column already exists
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'workspace_id' not in columns:
        print("Adding workspace_id column to users table...")
        cursor.execute("ALTER TABLE users ADD COLUMN workspace_id VARCHAR(64) DEFAULT 'personal' NOT NULL")
        conn.commit()
        print("Successfully added workspace_id column.")
    else:
        print("Column workspace_id already exists.")
    
    conn.close()
except Exception as e:
    print(f"Error: {e}")
    exit(1)
