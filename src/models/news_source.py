"""News source hierarchy.

Demonstrates **inheritance** (APISource and ScrapedSource inherit from
NewsSource) and **polymorphism** (both subclasses expose the same
`fetch_articles` method but implement it very differently).

The aggregator only talks to the abstract NewsSource interface, so adding
a new kind of source (RSS, Reddit, another API, ...) is just a matter of
writing one new subclass.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from .article import Article


class NewsSource(ABC):
    """Abstract base class for anything that can produce Articles."""

    def __init__(self, name: str) -> None:
        if not name:
            raise ValueError("NewsSource.name must be non-empty")
        self._name = name  # leading underscore = "treat as internal"

    @property
    def name(self) -> str:
        """Public read-only access to the source name."""
        return self._name

    @abstractmethod
    def fetch_articles(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 20,
    ) -> List[Article]:
        """Return a list of Articles matching the user's criteria.

        Subclasses MUST implement this. The abstract method enforces the
        interface — Python will refuse to instantiate any subclass that
        forgets to override it.
        """

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self._name!r}>"


class APISource(NewsSource):
    """A news source backed by an HTTP API client (e.g. NewsAPI)."""

    def __init__(self, name: str, client) -> None:
        # Call the parent constructor to set up self._name
        super().__init__(name)
        self._client = client  # any object exposing .fetch(query, category, page_size)

    def fetch_articles(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 20,
    ) -> List[Article]:
        payload = self._client.fetch(query=query, category=category, page_size=limit)
        items = payload.get("articles", []) if isinstance(payload, dict) else []

        articles: List[Article] = []
        for item in items[:limit]:
            try:
                articles.append(Article.from_newsapi(item, category=category))
            except ValueError:
                # Skip malformed entries instead of crashing the whole fetch.
                continue
        return articles


class ScrapedSource(NewsSource):
    """A news source backed by a web scraper (HTML pages, no API)."""

    def __init__(self, name: str, scraper, index_url: str) -> None:
        super().__init__(name)
        self._scraper = scraper  # any object exposing .scrape_index(url, limit)
        self._index_url = index_url

    def fetch_articles(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 20,
    ) -> List[Article]:
        items = self._scraper.scrape_index(self._index_url, limit=limit)

        articles: List[Article] = []
        for item in items:
            try:
                articles.append(
                    Article(
                        title=item["title"],
                        url=item["url"],
                        source=self.name,
                        description=item.get("description", ""),
                        category=category,
                    )
                )
            except (ValueError, KeyError):
                continue

        # Optional filtering by query (case-insensitive substring match)
        if query:
            q = query.lower()
            articles = [a for a in articles if q in a.title.lower()]

        return articles[:limit]