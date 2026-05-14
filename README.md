# News Aggregator

A Python information aggregator that combines **NewsAPI** + **web scraping**, with a **Tkinter GUI**, OOP architecture, response caching, data visualization and unit tests.

> 🚧 Work in progress.

## Project structure

    news-aggregator/
    ├── src/
    │   ├── models/          # Article, NewsSource (data models)
    │   ├── api/             # NewsAPI client
    │   ├── scraper/         # Web scraper with BeautifulSoup
    │   ├── aggregator/      # Orchestrator (API + scraping + cleanup)
    │   ├── cache/           # Disk cache
    │   ├── visualization/   # matplotlib charts
    │   └── gui/             # Tkinter UI
    ├── tests/               # Unit tests (unittest)
    ├── main.py              # Entry point
    ├── requirements.txt     # Dependencies
    ├── .env.example         # Environment variables template
    └── README.md

## Requirements

- Python 3.9 or newer
- A free API key from [NewsAPI.org](https://newsapi.org/register)

## Installation (provisional)

```bash