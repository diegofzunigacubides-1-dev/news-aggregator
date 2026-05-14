"""File-based response cache.

Stores arbitrary JSON-serialisable payloads on disk, keyed by a string
that the caller computes from the request parameters. Each entry carries
its own timestamp so we can expire stale data after `ttl_seconds`.

The cache is intentionally tiny and dependency-free — no Redis, no
sqlite, just a folder of JSON files. That keeps the project easy to run
on any machine.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Optional


class FileCache:
    """A very small key/value cache backed by JSON files in a folder."""

    def __init__(self, cache_dir: str = "cache", ttl_seconds: int = 3600) -> None:
        self._dir = Path(cache_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._ttl = ttl_seconds

    # ---------- Internal helpers ----------
    @staticmethod
    def make_key(*parts: Any) -> str:
        """Build a stable, filename-safe key from arbitrary parts.

        ``make_key("everything", "bitcoin", "business", 20)`` always
        returns the same short hash, regardless of insertion order or
        whitespace, so the same request maps to the same cache file.
        """
        raw = "|".join("" if p is None else str(p) for p in parts)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def _path_for(self, key: str) -> Path:
        return self._dir / f"{key}.json"

    # ---------- Public API ----------
    def get(self, key: str) -> Optional[Any]:
        """Return the cached value or None if missing/expired."""
        path = self._path_for(key)
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as f:
                entry = json.load(f)
        except (OSError, json.JSONDecodeError):
            # Corrupted file: drop it silently.
            path.unlink(missing_ok=True)
            return None

        timestamp = entry.get("timestamp", 0)
        if time.time() - timestamp > self._ttl:
            # Expired: clean up and behave as a miss.
            path.unlink(missing_ok=True)
            return None
        return entry.get("value")

    def set(self, key: str, value: Any) -> None:
        """Persist a value under `key` (overwrites any previous value)."""
        entry = {"timestamp": time.time(), "value": value}
        path = self._path_for(key)
        with path.open("w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False)

    def clear(self) -> int:
        """Delete every cached entry. Returns how many files were removed."""
        removed = 0
        for path in self._dir.glob("*.json"):
            path.unlink(missing_ok=True)
            removed += 1
        return removed