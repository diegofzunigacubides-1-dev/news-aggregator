"""Data visualization for the news aggregator.

Builds matplotlib Figures from aggregated statistics. Figures are returned
as objects (not shown via pyplot) so they can be either saved to disk OR
embedded inside the Tkinter GUI with FigureCanvasTkAgg.
"""
from __future__ import annotations

from collections import Counter
from typing import List

from matplotlib.figure import Figure

from src.models.article import Article


class ChartBuilder:
    """Creates matplotlib Figures describing a set of articles."""

    # A small, colour-blind-friendly palette reused across charts.
    PALETTE = [
        "#4C72B0", "#DD8452", "#55A868", "#C44E52",
        "#8172B3", "#937860", "#DA8BC3", "#8C8C8C",
    ]

    def __init__(self, figsize=(6, 4), dpi: int = 100) -> None:
        self._figsize = figsize
        self._dpi = dpi

    # ---------- Charts ----------
    def bar_by_source(self, stats: dict) -> Figure:
        """Horizontal bar chart: number of articles per source."""
        fig = Figure(figsize=self._figsize, dpi=self._dpi)
        ax = fig.add_subplot(111)

        if not stats:
            self._empty(ax, "No data to display")
            return fig

        # Sort sources by count, biggest first.
        items = sorted(stats.items(), key=lambda kv: kv[1], reverse=True)
        labels = [k for k, _ in items]
        values = [v for _, v in items]
        colors = [self.PALETTE[i % len(self.PALETTE)] for i in range(len(labels))]

        ax.barh(labels, values, color=colors)
        ax.invert_yaxis()  # biggest bar on top
        ax.set_xlabel("Number of articles")
        ax.set_title("Articles by source")
        # Annotate each bar with its value.
        for i, v in enumerate(values):
            ax.text(v, i, f" {v}", va="center")
        fig.tight_layout()
        return fig

    def pie_by_category(self, stats: dict) -> Figure:
        """Pie chart: share of articles per category."""
        fig = Figure(figsize=self._figsize, dpi=self._dpi)
        ax = fig.add_subplot(111)

        if not stats:
            self._empty(ax, "No data to display")
            return fig

        labels = list(stats.keys())
        values = list(stats.values())
        colors = [self.PALETTE[i % len(self.PALETTE)] for i in range(len(labels))]

        ax.pie(
            values,
            labels=labels,
            colors=colors,
            autopct="%1.0f%%",
            startangle=90,
        )
        ax.axis("equal")  # keep the pie circular
        ax.set_title("Articles by category")
        fig.tight_layout()
        return fig

    def timeline(self, articles: List[Article]) -> Figure:
        """Bar chart: number of articles published per day."""
        fig = Figure(figsize=self._figsize, dpi=self._dpi)
        ax = fig.add_subplot(111)

        dated = [a.best_date for a in articles if a.best_date is not None]
        if not dated:
            self._empty(ax, "No dated articles to display")
            return fig

        # Count articles per calendar day.
        per_day = Counter(d.date() for d in dated)
        days = sorted(per_day.keys())
        counts = [per_day[d] for d in days]
        labels = [d.strftime("%m-%d") for d in days]

        ax.bar(labels, counts, color=self.PALETTE[0])
        ax.set_xlabel("Publication date")
        ax.set_ylabel("Number of articles")
        ax.set_title("Articles over time")
        for i, c in enumerate(counts):
            ax.text(i, c, str(c), ha="center", va="bottom")
        fig.autofmt_xdate(rotation=45)
        fig.tight_layout()
        return fig

    # ---------- Helpers ----------
    @staticmethod
    def save(fig: Figure, path: str) -> str:
        """Write a Figure to disk as an image. Returns the path."""
        fig.savefig(path, bbox_inches="tight")
        return path

    @staticmethod
    def _empty(ax, message: str) -> None:
        """Render a friendly placeholder when there is nothing to plot."""
        ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=12)
        ax.set_xticks([])
        ax.set_yticks([])