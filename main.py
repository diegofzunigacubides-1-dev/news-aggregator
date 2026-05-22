"""Entry point for the News Aggregator application.

This module wires together all the components (cache, API client, source,
scraper, aggregator, chart builder) and hands them to the Tkinter GUI.
It is the only place that knows the concrete implementations — every other
module depends only on injected abstractions.
"""
from src.api.news_api_client import NewsAPIClient
from src.cache.file_cache import FileCache
from src.models import APISource
from src.scraper.web_scraper import WebScraper
from src.aggregator import NewsAggregator
from src.visualization import ChartBuilder
from src.gui import NewsAggregatorGUI


def build_aggregator() -> NewsAggregator:
    """Assemble the aggregator with a cached NewsAPI source and a scraper."""
    cache = FileCache(cache_dir="cache", ttl_seconds=3600)
    client = NewsAPIClient(cache=cache)
    api_source = APISource(name="NewsAPI", client=client)
    scraper = WebScraper()
    return NewsAggregator(sources=[api_source], scraper=scraper)


def main() -> None:
    """Build the app and start the GUI event loop."""
    aggregator = build_aggregator()
    chart_builder = ChartBuilder()
    gui = NewsAggregatorGUI(aggregator=aggregator, chart_builder=chart_builder)
    gui.run()


if __name__ == "__main__":
    main()