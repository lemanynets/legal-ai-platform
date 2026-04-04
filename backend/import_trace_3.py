import sys
import importlib

routers = [
    "app.routers.analyze",
    "app.routers.auto_process",
    "app.routers.audit",
    "app.routers.auth",
    "app.routers.billing",
    "app.routers.calculate",
    "app.routers.case_law",
    "app.routers.deadlines",
    "app.routers.documents",
    "app.routers.e_court",
    "app.routers.health",
    "app.routers.monitoring",
    "app.routers.opendatabot",
    "app.routers.strategy",
    "app.services.case_law_scheduler",
    "app.services.registry_monitor_scheduler"
]

print("starting trace")
for r in routers:
    print(f"importing {r}")
    try:
        importlib.import_module(r)
        print(f"imported {r}")
    except Exception as e:
        print(f"error importing {r}: {e}")
        
print("done")
