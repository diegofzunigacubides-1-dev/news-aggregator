"""Article data model.

Demonstrates encapsulation: internal attributes are wrapped by validation
in __post_init__, and derived data is exposed through @property methods so
the rest of the codebase never touches private state directly.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional


@dataclass
class Article:
    """A single news article.

    Most fields come from the NewsAPI response. The `*_scraped` fields are
    filled in later by the web scraper, when (and only when) it manages to
    enrich the article with extra data.
    """

    title: str
    url: str
    source: str
    description: str = ""
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    category: Optional[str] = None
    url_to_image: Optional[str] = None

    # Fields populated by the scraper (kept separate so we can tell what
    # came from the API vs. what we enriched ourselves).
    content_full: Optional[str] = None
    author_scraped: Optional[str] = None
    published_scraped: Optional[datetime] = None

    # ---------- Validation (runs after __init__) ----------
    def __post_init__(self) -> None:
        if not self.title or not isinstance(self.title, str):
            raise ValueError("Article.title must be a non-empty string")
        if not self.url or not self.url.startswith(("http://", "https://")):
            raise ValueError(f"Article.url must be a valid URL, got: {self.url!r}")
        if not self.source:
            raise ValueError("Article.source must be a non-empty string")

    # ---------- Derived properties (encapsulation) ----------
    @property
    def best_author(self) -> Optional[str]:
        """Prefer the scraped author (often more accurate) over the API one."""
        return self.author_scraped or self.author

    @property
    def best_date(self) -> Optional[datetime]:
        """Prefer the scraped publication date over the API one."""
        return self.published_scraped or self.published_at

    @property
    def is_enriched(self) -> bool:
        """True when the scraper has added at least one extra field."""
        return any(
            getattr(self, f) is not None
            for f in ("content_full", "author_scraped", "published_scraped")
        )

    # ---------- Helpers ----------
    def to_dict(self) -> dict:
        """Serialise the article to a plain dict (datetimes -> ISO strings)."""
        data = asdict(self)
        for key in ("published_at", "published_scraped"):
            if isinstance(data[key], datetime):
                data[key] = data[key].isoformat()
        return data

    @classmethod
    def from_newsapi(cls, payload: dict, category: Optional[str] = None) -> "Article":
        """Build an Article from a NewsAPI `articles` item.

        The NewsAPI shape is roughly::

            {
                "source": {"id": ..., "name": "BBC News"},
                "author": "...",
                "title": "...",
                "description": "...",
                "url": "...",
                "urlToImage": "...",
                "publishedAt": "2024-...Z",
                "content": "..."
            }
        """
        source_name = (payload.get("source") or {}).get("name", "Unknown")
        published_raw = payload.get("publishedAt")
        published: Optional[datetime] = None
        if published_raw:
            try:
                # NewsAPI returns ISO 8601 ending in 'Z'
                published = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
            except ValueError:
                published = None

        return cls(
            title=(payload.get("title") or "").strip(),
            url=payload.get("url") or "",
            source=source_name,
            description=(payload.get("description") or "").strip(),
            author=payload.get("author") or None,
            published_at=published,
            category=category,
            url_to_image=payload.get("urlToImage"),
        )

    def __str__(self) -> str:  # human-friendly representation
        date_str = self.best_date.strftime("%Y-%m-%d") if self.best_date else "—"
        return f"[{self.source} · {date_str}] {self.title}"