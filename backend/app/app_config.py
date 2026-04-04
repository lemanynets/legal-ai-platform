from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.lifespan import lifespan
from app.middleware import RequestIDMiddleware
from app.services.rate_limiting import get_user_or_ip_key


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

    # Rate limiting
    limiter = Limiter(key_func=get_user_or_ip_key, default_limits=[settings.rate_limit_default])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # CORS
    _cors_origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
    if not _cors_origins:
        _cors_origins = ["http://localhost:3000"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Demo-User", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
        max_age=600,
    )
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(SlowAPIMiddleware)

    return app