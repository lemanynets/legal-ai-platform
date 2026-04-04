from app.database import SessionLocal
from sqlalchemy import text

def check():
    db = SessionLocal()
    try:
        res = db.execute(text("SELECT id, user_id, title FROM knowledge_base_entries")).fetchall()
        print(f"Total entries: {len(res)}")
        for r in res:
            print(f"ID={r[0]}, USER={r[1]}, TITLE={r[2]}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check()
