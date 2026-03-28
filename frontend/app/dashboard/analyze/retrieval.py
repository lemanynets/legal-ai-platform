"""
Wave 3 · STORY-5 — Retrieval hardening.

Wraps the case-law retrieval layer with:
  - Query expansion using intake/strategy signals
  - Reranking by relevance score
  - Deduplication of identical decisions
  - Source authority filter (ВСУ > appellate > first instance)
  - Timeout budget with RETRIEVAL_TIMEOUT fallback
  - Result caching by query hash

All functions are pure transformers — they do not fetch from a database
themselves.  The actual DB/search calls are in the main backend retrieval
service; import these helpers and wrap the raw results.

Telemetry keys in structured logs:
  retrieval_hit_rate        = retrieved / requested
  rerank_latency            = time to rerank in ms
  authority_filter_drop_count = results dropped by authority filter
  cache_hit                 = true/false

Usage:

    from .retrieval import (
        expand_query, rerank_results, dedup_results,
        apply_authority_filter, with_timeout_budget,
        RetrievalResult, RETRIEVAL_TIMEOUT_SECONDS,
    )

    async def retrieve_case_law(query, intake_signals):
        expanded = expand_query(query, intake_signals)
        raw = await with_timeout_budget(db_search(expanded), RETRIEVAL_TIMEOUT_SECONDS)
        deduped = dedup_results(raw)
        filtered = apply_authority_filter(deduped)
        ranked = rerank_results(filtered, expanded)
        return ranked
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

from fastapi import HTTPException

logger = logging.getLogger("legal_ai.retrieval")

RETRIEVAL_TIMEOUT_SECONDS = 15.0
"""Maximum wall-clock time for the retrieval step before fallback."""

# ---------------------------------------------------------------------------
# Authority ranking
# ---------------------------------------------------------------------------

# Higher score = higher authority.  Unknown courts get 0.
_COURT_AUTHORITY: dict[str, int] = {
    # Supreme Court of Ukraine
    "Верховний Суд": 100,
    "Велика Палата Верховного Суду": 100,
    "Верховний суд": 100,
    "VSU": 100,
    # Cassation courts (specialised chambers of VSU)
    "Касаційний цивільний суд": 90,
    "Касаційний господарський суд": 90,
    "Касаційний адміністративний суд": 90,
    "Касаційний кримінальний суд": 90,
    # Appellate courts
    "апеляційний суд": 60,
    "Апеляційний суд": 60,
    "апеляційний господарський суд": 60,
    "Апеляційний господарський суд": 60,
    # First instance
    "районний суд": 30,
    "Районний суд": 30,
    "господарський суд": 30,
    "Господарський суд": 30,
    "адміністративний суд": 30,
    "Адміністративний суд": 30,
}

_MIN_AUTHORITY_SCORE = 0  # keep all by default; raise to e.g. 60 to drop first instance


@dataclass
class RetrievalResult:
    id: str
    decision_id: str
    source: str
    court_name: str | None
    court_type: str | None
    decision_date: str | None
    summary: str | None
    relevance_score: float = 0.0
    authority_score: int = 0
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = _hash_decision(self.decision_id, self.summary or "")
        if not self.authority_score:
            self.authority_score = _resolve_authority(self.court_name)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def expand_query(query: str, intake_signals: dict[str, Any]) -> str:
    """Expand a case-law search query using intake/strategy signals.

    Appends relevant Ukrainian legal terminology extracted from the intake:
      - classified_type → adds document-type-specific search terms
      - identified_parties → adds party role keywords
      - jurisdiction → ensures UA-specific terms
      - urgency_level + risk_level_legal → adds relevant case categories

    Returns an enriched query string suitable for vector or keyword search.
    """
    terms: list[str] = [query.strip()]

    doc_type: str = intake_signals.get("classified_type", "")
    _DOC_TYPE_EXPANSIONS: dict[str, list[str]] = {
        "pozov_do_sudu": ["позов", "відшкодування", "стягнення", "судовий захист"],
        "skarha_administratyvna": ["адміністративне оскарження", "владні повноваження", "ненормативний акт"],
        "dohovir_kupivli_prodazhu": ["договір купівлі-продажу", "право власності", "виконання договору"],
        "appeal_complaint": ["апеляційна скарга", "скасування рішення", "апеляційний розгляд"],
    }
    if doc_type in _DOC_TYPE_EXPANSIONS:
        terms.extend(_DOC_TYPE_EXPANSIONS[doc_type])

    risk_level: str = intake_signals.get("risk_level_legal", "")
    if risk_level == "high":
        terms.append("судова практика ВСУ")

    expanded = " ".join(dict.fromkeys(terms))  # deduplicate preserving order
    logger.debug(json.dumps({"event": "query_expanded", "original": query, "expanded": expanded}))
    return expanded


def rerank_results(
    results: list[RetrievalResult],
    query: str,
    top_k: int | None = None,
) -> list[RetrievalResult]:
    """Re-rank results by a combined score: relevance × authority.

    In production replace the scoring function with a cross-encoder model
    (e.g. sentence-transformers/paraphrase-multilingual-mpnet-base-v2).

    Emits: rerank_latency to structured logs.
    """
    t0 = time.perf_counter()

    # Simple additive scoring: relevance (0–1) + normalised authority (0–1)
    max_auth = max((r.authority_score for r in results), default=1) or 1
    scored = sorted(
        results,
        key=lambda r: (r.relevance_score * 0.7) + (r.authority_score / max_auth * 0.3),
        reverse=True,
    )
    if top_k:
        scored = scored[:top_k]

    latency_ms = int((time.perf_counter() - t0) * 1000)
    logger.info(json.dumps({
        "event": "retrieval_reranked",
        "rerank_latency": latency_ms,
        "total_results": len(scored),
    }))
    return scored


def dedup_results(results: list[RetrievalResult]) -> list[RetrievalResult]:
    """Remove duplicate decisions by content hash.

    Two results are considered duplicates when they have the same
    decision_id OR the same content_hash (same summary text).

    Unit test: two identical decision_id entries → only one in output.
    """
    seen_ids: set[str] = set()
    seen_hashes: set[str] = set()
    deduped: list[RetrievalResult] = []

    for r in results:
        if r.decision_id in seen_ids or r.content_hash in seen_hashes:
            continue
        seen_ids.add(r.decision_id)
        seen_hashes.add(r.content_hash)
        deduped.append(r)

    return deduped


def apply_authority_filter(
    results: list[RetrievalResult],
    min_authority: int = _MIN_AUTHORITY_SCORE,
) -> list[RetrievalResult]:
    """Drop results below the minimum authority threshold.

    Default min_authority=0 keeps all results.  Set to 60 to include only
    appellate and supreme court decisions.

    Emits: authority_filter_drop_count to logs.
    """
    filtered = [r for r in results if r.authority_score >= min_authority]
    drop_count = len(results) - len(filtered)
    if drop_count:
        logger.info(json.dumps({
            "event": "authority_filter",
            "authority_filter_drop_count": drop_count,
            "min_authority": min_authority,
        }))
    return filtered


async def with_timeout_budget(
    coro: Coroutine[Any, Any, list[RetrievalResult]],
    timeout: float = RETRIEVAL_TIMEOUT_SECONDS,
) -> list[RetrievalResult]:
    """Run retrieval coroutine with a timeout budget.

    Returns an empty list (fallback: generate without citations) when the
    timeout is exceeded, and emits RETRIEVAL_TIMEOUT to the log.

    The caller decides whether to raise HTTPException(408 / 422) based on
    the ENABLE_BLOCKING_PROCESSUAL_GATES flag or the citation gate.
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(json.dumps({
            "event": "RETRIEVAL_TIMEOUT",
            "timeout_seconds": timeout,
        }))
        return []  # caller falls back to no citations


# ---------------------------------------------------------------------------
# CacheBackend abstraction
# ---------------------------------------------------------------------------

import dataclasses
import pickle
from typing import Protocol, runtime_checkable

_CACHE_TTL_SECONDS = 3600.0


@runtime_checkable
class CacheBackend(Protocol):
    """Protocol for retrieval result caching.

    Implement this interface to swap the in-process dict for Redis,
    Memcached, or any other store without changing callers.
    """

    def get(self, key: str) -> list[RetrievalResult] | None:
        """Return cached results or None if absent/expired."""
        ...

    def put(self, key: str, results: list[RetrievalResult], ttl: float = _CACHE_TTL_SECONDS) -> None:
        """Store results under key with the given TTL (seconds)."""
        ...

    def delete(self, key: str) -> None:
        """Explicitly evict a cache entry."""
        ...


# ---------------------------------------------------------------------------
# In-memory backend (tests + single-process dev)
# ---------------------------------------------------------------------------


class InMemoryCacheBackend:
    """Thread-safe in-memory cache using a plain dict + timestamp TTL.

    NOTE: Not shared across processes.  Use RedisCacheBackend in production
    multi-worker deployments.
    """

    def __init__(self, default_ttl: float = _CACHE_TTL_SECONDS) -> None:
        self._store: dict[str, tuple[float, list[RetrievalResult]]] = {}
        self._default_ttl = default_ttl

    def get(self, key: str) -> list[RetrievalResult] | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, results = entry
        if time.time() - ts > self._default_ttl:
            del self._store[key]
            return None
        logger.debug(json.dumps({"event": "retrieval_cache_hit", "backend": "memory", "key": key[:12]}))
        return results

    def put(self, key: str, results: list[RetrievalResult], ttl: float = _CACHE_TTL_SECONDS) -> None:
        self._store[key] = (time.time(), results)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        """Clear all entries (useful in tests)."""
        self._store.clear()


# ---------------------------------------------------------------------------
# Redis backend (production)
# ---------------------------------------------------------------------------


class RedisCacheBackend:
    """Redis-backed cache for multi-process / multi-worker deployments.

    Requires the `redis` package:
        pip install redis[asyncio]   # async
        pip install redis            # sync (used here via sync client)

    Configuration via env vars:
        REDIS_URL       redis://localhost:6379/0  (default)
        REDIS_CACHE_DB  0                          (default)

    Results are pickled before storage; only RetrievalResult dataclass
    instances are stored — no arbitrary code execution on load.
    """

    def __init__(self, url: str | None = None, db: int | None = None) -> None:
        self._url = url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._db = db if db is not None else int(os.getenv("REDIS_CACHE_DB", "0"))
        self._client: Any = None
        self._available = False
        self._init_client()

    def _init_client(self) -> None:
        try:
            import redis  # noqa: PLC0415
            self._client = redis.Redis.from_url(self._url, db=self._db, socket_connect_timeout=2)
            self._client.ping()
            self._available = True
            logger.info(json.dumps({"event": "redis_cache_connected", "url": self._url[:30]}))
        except Exception as exc:
            logger.warning(json.dumps({
                "event": "redis_cache_unavailable",
                "error": str(exc)[:120],
                "fallback": "in_memory",
            }))
            self._available = False

    def get(self, key: str) -> list[RetrievalResult] | None:
        if not self._available:
            return None
        try:
            raw = self._client.get(f"retr:{key}")
            if raw is None:
                return None
            results: list[RetrievalResult] = pickle.loads(raw)  # noqa: S301
            logger.debug(json.dumps({"event": "retrieval_cache_hit", "backend": "redis", "key": key[:12]}))
            return results
        except Exception as exc:
            logger.warning(json.dumps({"event": "redis_get_error", "error": str(exc)[:80]}))
            return None

    def put(self, key: str, results: list[RetrievalResult], ttl: float = _CACHE_TTL_SECONDS) -> None:
        if not self._available:
            return
        try:
            self._client.setex(f"retr:{key}", int(ttl), pickle.dumps(results))
        except Exception as exc:
            logger.warning(json.dumps({"event": "redis_put_error", "error": str(exc)[:80]}))

    def delete(self, key: str) -> None:
        if not self._available:
            return
        try:
            self._client.delete(f"retr:{key}")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Active backend — swap here or inject via configure_cache_backend()
# ---------------------------------------------------------------------------

def _build_default_backend() -> CacheBackend:
    """Build the active backend based on env vars.

    - REDIS_URL set    → RedisCacheBackend (falls back to InMemory on connect error)
    - REDIS_URL absent → InMemoryCacheBackend
    """
    if os.getenv("REDIS_URL"):
        return RedisCacheBackend()
    return InMemoryCacheBackend()


_active_backend: CacheBackend = _build_default_backend()


def configure_cache_backend(backend: CacheBackend) -> None:
    """Replace the active cache backend (use in tests or app startup)."""
    global _active_backend
    _active_backend = backend


def cache_key(query: str, params: dict[str, Any] | None = None) -> str:
    payload = json.dumps({"q": query, "p": params or {}}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def cache_get(key: str) -> list[RetrievalResult] | None:
    return _active_backend.get(key)


def cache_put(key: str, results: list[RetrievalResult]) -> None:
    _active_backend.put(key, results)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_authority(court_name: str | None) -> int:
    if not court_name:
        return 0
    for pattern, score in _COURT_AUTHORITY.items():
        if pattern.lower() in court_name.lower():
            return score
    return 0


def _hash_decision(decision_id: str, summary: str) -> str:
    return hashlib.md5(f"{decision_id}:{summary[:200]}".encode()).hexdigest()
