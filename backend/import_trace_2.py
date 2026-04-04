import sys
print("starting e_court test")

try:
    print("importing app.routers.e_court")
    from app.routers import e_court
    print("imported e_court")
except Exception as e:
    print(f"Error: {e}")
