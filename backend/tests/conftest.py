from __future__ import annotations

import os


os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-pytest")
os.environ.setdefault("ALLOW_DEV_AUTH", "true")
os.environ.setdefault(
    "ALLOWED_DEV_DEMO_USERS",
    "demo-user,test-user,owner-user,admin-user,viewer-user,external-user,member-a,owner-a,owner-b,u1",
)
