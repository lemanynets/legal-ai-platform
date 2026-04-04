import faulthandler
import threading
import time
import sys

def dump_and_exit():
    time.sleep(5)
    print("=== FAULTHANDLER TIMEOUT ===", flush=True)
    faulthandler.dump_traceback(file=sys.stdout)
    sys.exit(1)

threading.Thread(target=dump_and_exit, daemon=True).start()

print("starting analyze trace", flush=True)
import app.routers.analyze
print("finished analyze trace", flush=True)
