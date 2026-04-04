import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

engine = sa.create_engine('postgresql+psycopg://legal_ai:legal_ai@localhost:5432/legal_ai')
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

try:
    res = db.execute(sa.text("SELECT id FROM public.user WHERE email = 'lemaninets1985@gmail.com'"))
    user_id = res.scalar()
    if not user_id:
        print("User not found!")
    else:
        print('User ID:', user_id)
        res = db.execute(sa.text("SELECT id FROM public.subscription WHERE user_id = :uid ORDER BY created_at DESC LIMIT 1"), {'uid': user_id})
        sub_id = res.scalar()
        if not sub_id:
            print('No sub found!')
        else:
            print('Updating sub:', sub_id)
            db.execute(sa.text("UPDATE public.subscription SET plan = 'PRO_PLUS', status = 'active', analyses_limit = NULL, docs_limit = NULL WHERE id = :sid"), {'sid': sub_id})
            db.commit()
            print('Done!')
finally:
    db.close()
