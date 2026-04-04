import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
import datetime

# Try localhost
db_url = 'postgresql+psycopg://legal_ai:legal_ai@localhost:5432/legal_ai'
print(f"Connecting to {db_url}...")

try:
    print("Creating engine...")
    engine = sa.create_engine(db_url, connect_args={"connect_timeout": 5})
    print("Creating session...")
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    print("Executing user query...")
    res = db.execute(sa.text("SELECT id FROM \"user\" WHERE email = 'lemaninets1985@gmail.com'"))
    print("Query executed.")
    user_id = res.scalar()
    
    if not user_id:
        print('User not found in "user" table. Checking for other users...')
        res = db.execute(sa.text("SELECT id, email FROM \"user\" LIMIT 5"))
        for row in res:
            print(f"Found user: {row[0]} ({row[1]})")
        
        # If still not found, search in User (case sensitive?)
        try:
            res = db.execute(sa.text("SELECT id FROM \"User\" WHERE email = 'lemaninets1985@gmail.com'"))
            user_id = res.scalar()
        except:
            pass
            
    if not user_id:
        print('User lemaninets1985@gmail.com not found.')
    else:
        print('User ID:', user_id)
        # Check for subscription
        res = db.execute(sa.text("SELECT id FROM subscription WHERE user_id = :uid ORDER BY created_at DESC LIMIT 1"), {'uid': user_id})
        sub_id = res.scalar()
        
        if not sub_id:
            print('No sub found! Creating one...')
            now = datetime.datetime.now()
            forever = datetime.datetime(2100, 1, 1)
            db.execute(sa.text("INSERT INTO subscription (user_id, plan, status, analyses_used, analyses_limit, docs_used, docs_limit, current_period_start, current_period_end) VALUES (:uid, 'PRO_PLUS', 'active', 0, NULL, 0, NULL, :start, :end)"), 
                       {'uid': user_id, 'start': now, 'end': forever})
        else:
            print('Updating sub:', sub_id)
            forever = datetime.datetime(2100, 1, 1)
            db.execute(sa.text("UPDATE subscription SET plan = 'PRO_PLUS', status = 'active', analyses_limit = NULL, docs_limit = NULL, current_period_end = :end WHERE id = :sid"), 
                       {'sid': sub_id, 'end': forever})
            
        db.commit()
        print('Successfully updated to PRO_PLUS!')
    db.close()
except Exception as e:
    print('Error:', e)
