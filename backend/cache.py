"""
Request Cache
-------------
Two-layer caching:
  1. Exact cache  — SHA-256 of (topic.lower + grade + slides + subject.lower)
  2. Soft cache   — same exact key, but TTL-based (8h default)

For the bonus semantic cache (embeddings), see cache_semantic.py.
This layer alone handles repeat requests which are common in schools
(same teacher regenerating, multiple teachers on same topic).

Estimated hit rate: 15-25% based on topic frequency patterns in EdTech.
"""

import hashlib
import os
import time
from dataclasses import dataclass, field
from typing import Optional

# Cache TTL from environment (hours), converted to seconds
_TTL_HOURS = int(os.environ.get("CACHE_TTL_HOURS", "8"))
TTL_SECONDS = _TTL_HOURS * 60 * 60


@dataclass
class CacheEntry:
    result: dict
    created_at: float = field(default_factory=time.time)
    hits: int = 0

    def is_fresh(self) -> bool:
        return (time.time() - self.created_at) < TTL_SECONDS


class PPTCache:
    def __init__(self):
        self._store: dict[str, CacheEntry] = {}
        self.stats = {"hits": 0, "misses": 0, "inr_saved": 0.0}

    def _key(self, topic: str, grade: int, slides: int, subject: str) -> str:
        raw = f"{topic.lower().strip()}|{grade}|{slides}|{subject.lower().strip()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def get(self, topic: str, grade: int, slides: int, subject: str) -> Optional[dict]:
        key = self._key(topic, grade, slides, subject)
        entry = self._store.get(key)
        if entry and entry.is_fresh():
            entry.hits += 1
            self.stats["hits"] += 1
            return entry.result
        if entry:
            del self._store[key]  # evict stale
        self.stats["misses"] += 1
        return None

    def set(self, topic: str, grade: int, slides: int, subject: str, result: dict):
        key = self._key(topic, grade, slides, subject)
        self._store[key] = CacheEntry(result=result)

    def record_savings(self, amount_inr: float):
        self.stats["inr_saved"] += amount_inr

    def summary(self) -> dict:
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total * 100) if total else 0
        return {
            **self.stats,
            "total_requests": total,
            "hit_rate_pct": round(hit_rate, 1),
            "cache_size": len(self._store),
        }


# Module-level singleton (in prod this would be Redis)
cache = PPTCache()