"""HTML scraper for news articles.

Extracts content, author and publication date from an article page using
heuristics that work for most news sites:

  * Author / date: standardised <meta> tags (Open Graph, Schema.org).
  * Body: the <article> element, falling back to long <p> blocks.

The scraper is intentionally tolerant — if a field cannot be extracted it
returns None instead of raising, so the aggregator keeps working with
whatever data it managed to recover.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

from src.models.article import Article


class ScraperError(Exception):
    """Raised when the scraper cannot reach or read a page at all."""


class WebScraper:
    """Lightweight, polite HTML scraper for news article pages."""

    # Identify ourselves with a realistic browser User-Agent string. Many
    # sites return an error page to default Python User-Agents.
    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36 NewsAggregator/1.0"
    )

    # Meta tag names commonly used for the author of the page.
    AUTHOR_META = [
        ("property", "article:author"),
        ("name", "author"),
        ("name", "byl"),
        ("name", "DC.creator"),
    ]

    # Meta tag names commonly used for the publication date.
    DATE_META = [
        ("property", "article:published_time"),
        ("name", "pubdate"),
        ("name", "publishdate"),
        ("itemprop", "datePublished"),
        ("name", "DC.date.issued"),
    ]

    def __init__(self, user_agent: Optional[str] = None, timeout: int = 10) -> None:
        self._headers = {"User-Agent": user_agent or self.DEFAULT_USER_AGENT}
        self._timeout = timeout

    # ---------- Public API ----------
    def scrape_url(self, url: str) -> dict:
        """Download `url`, parse it and return whatever fields we recovered.

        Returns a dict with keys ``content``, ``author`` and ``published_at``
        (any of them can be None).
        """
        html = self._download(url)
        soup = BeautifulSoup(html, "lxml")
        return {
            "content": self._extract_content(soup),
            "author": self._extract_author(soup),
            "published_at": self._extract_date(soup),
        }

    def enrich_article(self, article: Article) -> Article:
        """Scrape the article URL and fill in its `*_scraped` fields.

        Returns the same Article instance for chaining. Errors are caught
        so that a single bad page never breaks a batch enrichment.
        """
        try:
            data = self.scrape_url(article.url)
        except ScraperError:
            return article

        article.content_full = data["content"]
        article.author_scraped = data["author"]
        article.published_scraped = data["published_at"]
        return article

    # ---------- Internals ----------
    def _download(self, url: str) -> str:
        try:
            response = requests.get(url, headers=self._headers, timeout=self._timeout)
        except requests.RequestException as exc:
            raise ScraperError(f"Network error fetching {url}: {exc}") from exc
        if response.status_code != 200:
            raise ScraperError(f"HTTP {response.status_code} fetching {url}")
        return response.text

    def _meta_value(self, soup: BeautifulSoup, candidates) -> Optional[str]:
        """Return the first non-empty <meta> value matching the candidates."""
        for attr, value in candidates:
            tag = soup.find("meta", attrs={attr: value})
            if tag and tag.get("content"):
                return tag["content"].strip()
        return None

    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        author = self._meta_value(soup, self.AUTHOR_META)
        if author:
            return author
        # Fallback: element with rel="author"
        tag = soup.find(attrs={"rel": "author"})
        if tag and tag.get_text(strip=True):
            return tag.get_text(strip=True)
        return None

    def _extract_date(self, soup: BeautifulSoup) -> Optional[datetime]:
        raw = self._meta_value(soup, self.DATE_META)
        if not raw:
            # Fallback: <time datetime="...">
            time_tag = soup.find("time", attrs={"datetime": True})
            if time_tag:
                raw = time_tag["datetime"]
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _extract_content(self, soup: BeautifulSoup) -> Optional[str]:
        # Best case: an <article> tag wraps the body.
        article = soup.find("article")
        if article:
            paragraphs = [
                p.get_text(" ", strip=True)
                for p in article.find_all("p")
                if p.get_text(strip=True)
            ]
            if paragraphs:
                return "\n\n".join(paragraphs)

        # Fallback: collect long paragraphs from anywhere in the page.
        long_paragraphs = [
            p.get_text(" ", strip=True)
            for p in soup.find_all("p")
            if len(p.get_text(strip=True)) > 80
        ]
        if long_paragraphs:
            return "\n\n".join(long_paragraphs[:10])  # cap to avoid huge dumps
        return None