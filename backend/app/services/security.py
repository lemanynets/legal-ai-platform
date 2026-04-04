import logging
from datetime import datetime, timedelta
from secrets import token_urlsafe

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

logger = logging.getLogger(__name__)

_LOCAL_ENVS = {"local", "dev", "development", "test"}


def _resolve_secret_key() -> str:
    configured = getattr(settings, "jwt_secret_key", "").strip()
    if configured:
        return configured
    if settings.app_env in _LOCAL_ENVS:
        logger.warning("JWT_SECRET_KEY missing; using ephemeral development key for current process only.")
        return token_urlsafe(48)
    raise ValueError(
        'JWT_SECRET_KEY environment variable is required. Generate with: python -c "import secrets; print(secrets.token_urlsafe(64))"'
    )


SECRET_KEY = _resolve_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Prefer pbkdf2_sha256 for new hashes to avoid bcrypt backend issues on some
# platforms and to support long passwords safely, while still accepting legacy
# bcrypt_sha256 / bcrypt hashes already stored in the database.
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt_sha256", "bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update(
        {
            "exp": expire,
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": datetime.utcnow(),
        }
    )
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
        )
    except JWTError:
        if not settings.allow_legacy_jwt:
            return None
        try:
            payload = jwt.decode(
                token,
                SECRET_KEY,
                algorithms=[ALGORITHM],
                options={"verify_aud": False},
            )
            if payload.get("iss") not in (None, settings.jwt_issuer):
                return None
            return payload
        except JWTError:
            return None
