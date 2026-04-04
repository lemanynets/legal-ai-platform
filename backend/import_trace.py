import sys
print("starting import test")

try:
    print("importing config")
    from app.config import settings
    print("imported config")
    
    print("importing database")
    from app.database import get_db
    print("imported database")
    
    print("importing main")
    from app.main import app
    print("imported main")
except Exception as e:
    import traceback
    traceback.print_exc()
