import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
import datetime

# Use the database URL from settings or just standard local dev
db_url = 'postgresql+psycopg://legal_ai:legal_ai@localhost:5432/legal_ai'
print(f"Connecting to {db_url}...")

try:
    engine = sa.create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    email = 'lemaninets1985@gmail.com'
    res = db.execute(sa.text("SELECT id FROM \"user\" WHERE email = :email"), {'email': email})
    user_id = res.scalar()
    
    if not user_id:
        print(f"User {email} not found.")
    else:
        print(f"Found User ID: {user_id}")
        
        # We want "no end date", so let's set it to year 2100
        infinity_date = datetime.datetime(2100, 1, 1)
        
        # Check for existing subscription
        res = db.execute(sa.text("SELECT id FROM subscription WHERE user_id = :uid"), {'uid': user_id})
        subscription = res.fetchone()
        
        if subscription:
            sub_id = subscription[0]
            print(f"Updating subscription {sub_id} to PRO_PLUS (Lifetime-ish)...")
            db.execute(sa.text("""
                UPDATE subscription 
                SET plan = 'PRO_PLUS', 
                    status = 'active', 
                    analyses_limit = NULL, 
                    docs_limit = NULL, 
                    current_period_end = :infinity
                WHERE id = :sid
            """), {'sid': sub_id, 'infinity': infinity_date})
        else:
            print("Creating new PRO_PLUS subscription...")
            db.execute(sa.text("""
                INSERT INTO subscription (user_id, plan, status, analyses_used, analyses_limit, docs_used, docs_limit, current_period_start, current_period_end)
                VALUES (:uid, 'PRO_PLUS', 'active', 0, NULL, 0, NULL, :now, :infinity)
            """), {'uid': user_id, 'now': datetime.datetime.now(), 'infinity': infinity_date})
            
        db.commit()
        print("Success: Account upgraded to PRO_PLUS until 2100!")
    
    db.close()
except Exception as e:
    print(f"Error during upgrade: {e}")
