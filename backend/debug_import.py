
try:
    from app.main import app
    print("App imported successfully")
except Exception as e:
    import traceback
    print("Error importing app:")
    traceback.print_exc()
