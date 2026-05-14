"""HTTP client for NewsAPI.org.

Responsibilities:
  * Build NewsAPI requests from high-level parameters (query, category, etc.)
  * Consult the cache before hitting the network.
  * Translate HTTP errors into a clean Python exception.

The client is intentionally thin — it returns the raw JSON payload and
lets the calling code decide how to turn it into Article objects. This
keeps it easy to test and easy to swap for another news API later.
"""
from __future__ import annotations

import os
from typing import Optional

import requests
from dotenv import load_dotenv

from src.cache.file_cache import FileCache


# Load environment variables from .env once when this module is imported.
load_dotenv()


class NewsAPIError(Exception):
    """Raised when the NewsAPI request fails for any reason."""


class NewsAPIClient:
    """Minimal client for the NewsAPI.org `/v2/top-headlines` endpoint."""

    BASE_URL = "https://newsapi.org/v2"

    # NewsAPI accepts these categories on /v2/top-headlines.
    VALID_CATEGORIES = {
        "business", "entertainment", "general", "health",
        "science", "sports", "technology",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        cache: Optional[FileCache] = None,
        country: str = "us",
        timeout: int = 10,
    ) -> None:
        self._api_key = api_key or os.getenv("NEWS_API_KEY")
        if not self._api_key:
            raise NewsAPIError(
                "Missing NewsAPI key. Set NEWS_API_KEY in .env or pass api_key=..."
            )
        self._cache = cache or FileCache()
        self._country = country
        self._timeout = timeout

    # ---------- Public API ----------
    def fetch(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        page_size: int = 20,
    ) -> dict:
        """Return a NewsAPI payload (already parsed as a dict).

        ``query`` is a free-text search; ``category`` is one of the values
        in :attr:`VALID_CATEGORIES`. Either or both can be supplied.
        """
        if category and category not in self.VALID_CATEGORIES:
            raise NewsAPIError(
                f"Invalid category {category!r}. "
                f"Choose one of: {sorted(self.VALID_CATEGORIES)}"
            )
        page_size = max(1, min(100, int(page_size)))  # NewsAPI caps at 100

        cache_key = FileCache.make_key(
            "top-headlines", self._country, query, category, page_size
        )
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        params = {
            "country": self._country,
            "pageSize": page_size,
            "apiKey": self._api_key,
        }
        if query:
            params["q"] = query
        if category:
            params["category"] = category

        try:
            response = requests.get(
                f"{self.BASE_URL}/top-headlines",
                params=params,
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise NewsAPIError(f"Network error: {exc}") from exc

        if response.status_code != 200:
            raise NewsAPIError(
                f"NewsAPI returned HTTP {response.status_code}: {response.text[:200]}"
            )

        payload = response.json()
        if payload.get("status") != "ok":
            raise NewsAPIError(f"NewsAPI error: {payload.get('message', 'unknown')}")

        # Store in the cache only on success.
        self._cache.set(cache_key, payload)
        return payload