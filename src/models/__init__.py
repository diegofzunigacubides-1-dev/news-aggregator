"""Data models for the news aggregator."""
from .article import Article
from .news_source import NewsSource, APISource, ScrapedSource

__all__ = ["Article", "NewsSource", "APISource", "ScrapedSource"]