from __future__ import annotations

from pathlib import Path
import httpx

from app.config import settings


def _sanitize_segment(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in value.strip())
    cleaned = cleaned.strip("._")
    return cleaned or "item"


def get_storage_root() -> Path:
    root = Path(settings.document_storage_root)
    if not root.is_absolute():
        # Resolve relative paths from backend root.
        root = (Path(__file__).resolve().parents[2] / root).resolve()
    return root


def build_export_rel_path(*, user_id: str, document_id: str, extension: str) -> str:
    ext = extension.lower().lstrip(".")
    safe_user = _sanitize_segment(user_id)
    safe_doc = _sanitize_segment(document_id)
    return f"{safe_user}/{safe_doc}.{ext}"


def _resolve_under_root(relative_path: str) -> Path:
    root = get_storage_root()
    path = (root / relative_path).resolve()
    if path != root and root not in path.parents:
        raise ValueError("Path is outside of document storage root")
    return path


def _get_supabase_url(relative_path: str) -> str | None:
    if not settings.supabase_url or not settings.supabase_anon_key:
        return None
    url = settings.supabase_url.rstrip("/")
    bucket = settings.supabase_storage_bucket.strip()
    return f"{url}/storage/v1/object/{bucket}/{relative_path}"


def _get_supabase_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.supabase_anon_key}",
        "apikey": settings.supabase_anon_key,
    }


def read_export_bytes(relative_path: str | None) -> bytes | None:
    if not relative_path:
        return None
        
    storage_url = _get_supabase_url(relative_path)
    if storage_url:
        try:
            resp = httpx.get(storage_url, headers=_get_supabase_headers(), timeout=10.0)
            if resp.status_code == 200:
                return resp.content
        except Exception:
            pass

    try:
        path = _resolve_under_root(relative_path)
    except ValueError:
        return None
    if not path.exists() or not path.is_file():
        return None
    return path.read_bytes()


def write_export_bytes(*, relative_path: str, content: bytes) -> str:
    # Try Supabase Storage first
    storage_url = _get_supabase_url(relative_path)
    if storage_url:
        try:
            headers = _get_supabase_headers()
            headers["Content-Type"] = "application/octet-stream"
            headers["x-upsert"] = "true"
            resp = httpx.post(storage_url, headers=headers, content=content, timeout=15.0)
            if resp.status_code in {200, 201}:
                return relative_path
            # if POST failed due to existing, maybe try PUT?
            if resp.status_code == 400:
                httpx.put(storage_url, headers=headers, content=content, timeout=15.0)
        except Exception:
            pass

    # Fallback to local
    path = _resolve_under_root(relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return relative_path


def delete_export_file(relative_path: str | None) -> bool:
    if not relative_path:
        return False
        
    storage_url = _get_supabase_url(relative_path)
    if storage_url:
        try:
            resp = httpx.delete(storage_url, headers=_get_supabase_headers(), timeout=10.0)
            if resp.status_code in {200, 204}:
                return True
        except Exception:
            pass

    try:
        path = _resolve_under_root(relative_path)
    except ValueError:
        return False
    if not path.exists() or not path.is_file():
        return False
    path.unlink()
    return True


def get_signed_url(relative_path: str | None, expires_in: int = 3600) -> str | None:
    if not relative_path:
        return None
        
    storage_url = _get_supabase_url(relative_path)
    if storage_url:
        try:
            # Supabase Sign URL endpoint: POST /storage/v1/object/sign/{bucket}/{path}
            # storage_url currently is /storage/v1/object/{bucket}/{path}
            # We need to inject 'sign' after 'object'
            sign_url = storage_url.replace("/storage/v1/object/", "/storage/v1/object/sign/")
            resp = httpx.post(
                sign_url, 
                headers=_get_supabase_headers(),
                json={"expiresIn": expires_in},
                timeout=10.0
            )
            if resp.status_code == 200:
                data = resp.json()
                signed_path = data.get("signedURL")
                if signed_path:
                    # Supabase returns relative path to the API, we need absolute
                    base_url = settings.supabase_url.rstrip("/")
                    return f"{base_url}/storage/v1{signed_path}"
        except Exception:
            pass
            
    # Local storage doesn't support signed URLs easily without a proxy
    return None
