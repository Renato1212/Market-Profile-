"""
Multi-tier caching layer: in-memory (TTL dict) + SQLite persistence.
Eliminates redundant API calls and ensures graceful degradation.
"""
import json
import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional, Callable
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class MemoryCache:
    """Thread-safe in-memory TTL cache for hot path data."""

    def __init__(self):
        self._store: dict[str, tuple[Any, datetime]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key in self._store:
                value, expires_at = self._store[key]
                if datetime.utcnow() < expires_at:
                    return value
                del self._store[key]
        return None

    async def set(self, key: str, value: Any, ttl_seconds: int = 300):
        async with self._lock:
            self._store[key] = (value, datetime.utcnow() + timedelta(seconds=ttl_seconds))

    async def delete(self, key: str):
        async with self._lock:
            self._store.pop(key, None)

    async def clear_expired(self):
        async with self._lock:
            now = datetime.utcnow()
            expired = [k for k, (_, exp) in self._store.items() if now >= exp]
            for k in expired:
                del self._store[k]

    def size(self) -> int:
        return len(self._store)


# Global singleton
_cache = MemoryCache()


async def get_cached(key: str) -> Optional[Any]:
    return await _cache.get(key)


async def set_cached(key: str, value: Any, ttl_seconds: int = 300):
    await _cache.set(key, value, ttl_seconds)


async def get_or_fetch(
    key: str,
    fetch_fn: Callable,
    ttl_seconds: int = 300,
    fallback_fn: Optional[Callable] = None,
) -> Optional[Any]:
    """
    Cache-aside pattern with fallback support.
    1. Check memory cache
    2. If miss, call fetch_fn
    3. If fetch fails, try fallback_fn
    4. Store result in cache
    """
    cached = await _cache.get(key)
    if cached is not None:
        return cached

    try:
        if asyncio.iscoroutinefunction(fetch_fn):
            result = await fetch_fn()
        else:
            result = fetch_fn()

        if result is not None:
            await _cache.set(key, result, ttl_seconds)
            return result

    except Exception as e:
        logger.warning(f"Cache fetch_fn failed for key={key}: {e}")

    if fallback_fn is not None:
        try:
            if asyncio.iscoroutinefunction(fallback_fn):
                result = await fallback_fn()
            else:
                result = fallback_fn()
            if result is not None:
                await _cache.set(key, result, ttl_seconds // 2)
                return result
        except Exception as e:
            logger.warning(f"Cache fallback_fn failed for key={key}: {e}")

    return None


def cache_key(*parts) -> str:
    """Generate a deterministic cache key from parts."""
    joined = "|".join(str(p) for p in parts)
    return hashlib.md5(joined.encode()).hexdigest()[:16] + "_" + joined[:60]


# DB-backed cache for persistence across restarts
async def get_db_cache(key: str, db_session) -> Optional[Any]:
    """Check SQLite data_cache table."""
    try:
        from sqlalchemy import select, text
        from models.database import DataCache

        result = await db_session.execute(
            select(DataCache).where(
                DataCache.key == key,
                DataCache.expires_at > datetime.utcnow()
            )
        )
        row = result.scalar_one_or_none()
        if row:
            return json.loads(row.value)
    except Exception as e:
        logger.debug(f"DB cache miss for {key}: {e}")
    return None


async def set_db_cache(key: str, value: Any, ttl_seconds: int, db_session):
    """Store in SQLite data_cache table."""
    try:
        from models.database import DataCache

        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        json_val = json.dumps(value, default=str)

        existing = await db_session.get(DataCache, key)
        if existing:
            existing.value = json_val
            existing.expires_at = expires_at
        else:
            cache_row = DataCache(key=key, value=json_val, expires_at=expires_at)
            db_session.add(cache_row)

        await db_session.commit()
    except Exception as e:
        logger.warning(f"DB cache write error for {key}: {e}")


# TTL constants (seconds)
TTL = {
    "daily_ohlcv": 86400,
    "intraday_market_hours": 60,
    "intraday_after_hours": 3600,
    "options_chain": 900,
    "ai_plan": 86400,
    "cot": 604800,
    "vix_macro": 300,
    "pc_ratio": 3600,
    "gex": 900,
}
