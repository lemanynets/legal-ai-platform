from starlette.middleware.base import BaseHTTPMiddleware
import uuid
from fastapi import Request, Response


def RequestIDMiddleware(app):
    class _RequestIDMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
    return _RequestIDMiddleware(app)