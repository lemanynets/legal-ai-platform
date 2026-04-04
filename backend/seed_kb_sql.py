from app.database import SessionLocal
from app.models.knowledge_base import KnowledgeBaseEntry
from sqlalchemy import text

def seed():
    db = SessionLocal()
    # Get any user id
    user = db.execute(text("SELECT id FROM users LIMIT 1")).fetchone()
    if not user:
        print("No users found")
        db.close()
        return
    
    user_id = user[0]
    print(f"Seeding for user: {user_id}")
    
    entries = [
        KnowledgeBaseEntry(
            title="Zrazok Poinovnoiy (Standard)",
            content="This is a golden standard for pleading. Argument A, Argument B.",
            category="Pleading",
            user_id=user_id
        ),
        KnowledgeBaseEntry(
            title="Zrazok Dogovoru (Complex)",
            content="This is a golden standard for complex service contracts. Section 1: Parties, Section 2: Subject.",
            category="Contract",
            user_id=user_id
        )
    ]
    
    db.add_all(entries)
    db.commit()
    print("Seeded successfully!")
    db.close()

if __name__ == "__main__":
    seed()
