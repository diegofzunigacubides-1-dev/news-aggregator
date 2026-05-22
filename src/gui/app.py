"""Tkinter GUI for the news aggregator.

The window is split into three areas: a control panel (top), a notebook
with an "Articles" tab and a "Charts" tab (centre), and a status bar
(bottom).

Threading note: network calls run in a daemon background thread so the
window never freezes. The worker thread never touches widgets directly —
it hands results back to the main thread through ``root.after()``.
"""
from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from tkinter import ttk, messagebox

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class NewsAggregatorGUI:
    """Main application window for the news aggregator."""

    # "(any)" maps to None so the user can fetch without a category.
    CATEGORIES = [
        "(any)", "business", "entertainment", "general",
        "health", "science", "sports", "technology",
    ]

    def __init__(self, aggregator, chart_builder) -> None:
        # Dependencies are injected, so the GUI is decoupled from the
        # concrete aggregator / chart implementations.
        self._aggregator = aggregator
        self._chart_builder = chart_builder
        self._articles = []

        self.root = tk.Tk()
        self.root.title("News Aggregator")
        self.root.geometry("1024x680")
        self.root.minsize(820, 520)

        self._build_controls()
        self._build_body()
        self._build_statusbar()

    # ---------- UI construction ----------
    def _build_controls(self) -> None:
        """Top panel: category, search text, count, enrich, fetch button."""
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(frame, text="Category:").grid(row=0, column=0, padx=4)
        self._category_var = tk.StringVar(value="technology")
        ttk.Combobox(
            frame, textvariable=self._category_var, values=self.CATEGORIES,
            state="readonly", width=14,
        ).grid(row=0, column=1, padx=4)

        ttk.Label(frame, text="Search:").grid(row=0, column=2, padx=4)
        self._query_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self._query_var, width=22).grid(
            row=0, column=3, padx=4
        )

        ttk.Label(frame, text="Articles:").grid(row=0, column=4, padx=4)
        self._limit_var = tk.IntVar(value=15)
        ttk.Spinbox(
            frame, from_=1, to=100, textvariable=self._limit_var, width=5,
        ).grid(row=0, column=5, padx=4)

        self._enrich_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame, text="Enrich (scrape)", variable=self._enrich_var,
        ).grid(row=0, column=6, padx=4)

        self._fetch_btn = ttk.Button(
            frame, text="Fetch news", command=self._on_fetch,
        )
        self._fetch_btn.grid(row=0, column=7, padx=8)

    def _build_body(self) -> None:
        """Centre: a notebook with the 'Articles' and 'Charts' tabs."""
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # --- Articles tab: list on the left, detail on the right ---
        articles_tab = ttk.Frame(notebook)
        notebook.add(articles_tab, text="Articles")

        paned = ttk.PanedWindow(articles_tab, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(paned)
        scrollbar = ttk.Scrollbar(left, orient=tk.VERTICAL)
        self._listbox = tk.Listbox(left, yscrollcommand=scrollbar.set)
        scrollbar.config(command=self._listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._listbox.bind("<<ListboxSelect>>", self._on_select_article)
        paned.add(left, weight=2)

        right = ttk.Frame(paned)
        self._detail = tk.Text(
            right, wrap=tk.WORD, state=tk.DISABLED, padx=8, pady=8, width=44,
        )
        self._detail.pack(fill=tk.BOTH, expand=True)
        self._open_btn = ttk.Button(
            right, text="Open in browser", command=self._open_in_browser,
            state=tk.DISABLED,
        )
        self._open_btn.pack(pady=6)
        paned.add(right, weight=3)

        # --- Charts tab (populated after every fetch) ---
        self._charts_tab = ttk.Frame(notebook)
        notebook.add(self._charts_tab, text="Charts")

    def _build_statusbar(self) -> None:
        """Bottom: a single-line status label."""
        self._status_var = tk.StringVar(
            value="Ready. Pick a category and click 'Fetch news'."
        )
        ttk.Label(
            self.root, textvariable=self._status_var,
            relief=tk.SUNKEN, anchor=tk.W, padding=4,
        ).pack(side=tk.BOTTOM, fill=tk.X)

    # ---------- Event handlers ----------
    def _on_fetch(self) -> None:
        """Triggered by the 'Fetch news' button.

        Reads the form, then launches a background thread so the window
        keeps responding while the network request runs.
        """
        self._fetch_btn.config(state=tk.DISABLED)
        self._status_var.set("Fetching news, please wait...")

        category = self._category_var.get()
        category = None if category == "(any)" else category
        query = self._query_var.get().strip() or None
        limit = self._limit_var.get()
        enrich = self._enrich_var.get()

        worker = threading.Thread(
            target=self._fetch_worker,
            args=(query, category, limit, enrich),
            daemon=True,  # dies automatically when the app closes
        )
        worker.start()

    def _fetch_worker(self, query, category, limit, enrich) -> None:
        """Runs in the background thread. Must NOT touch widgets directly."""
        try:
            articles = self._aggregator.aggregate(
                query=query, category=category,
                limit_per_source=limit, enrich=enrich,
            )
            # Hand the result back to the main thread.
            self.root.after(0, self._on_fetch_done, articles, None)
        except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
            self.root.after(0, self._on_fetch_done, [], str(exc))

    def _on_fetch_done(self, articles, error) -> None:
        """Runs on the main thread once the worker finished."""
        self._fetch_btn.config(state=tk.NORMAL)
        if error:
            self._status_var.set("Error while fetching news.")
            messagebox.showerror("Fetch failed", error)
            return

        self._articles = articles
        self._listbox.delete(0, tk.END)
        for article in articles:
            self._listbox.insert(tk.END, str(article))
        self._status_var.set(f"Loaded {len(articles)} article(s).")
        self._render_charts()

    def _on_select_article(self, event=None) -> None:
        """Show the details of the article selected in the list."""
        selection = self._listbox.curselection()
        if not selection:
            return
        self._show_detail(self._articles[selection[0]])

    def _show_detail(self, article) -> None:
        """Fill the detail text box with everything we know about `article`."""
        date = article.best_date
        lines = [
            article.title,
            "",
            f"Source   : {article.source}",
            f"Author   : {article.best_author or 'unknown'}",
            f"Date     : {date.strftime('%Y-%m-%d %H:%M') if date else 'unknown'}",
            f"Category : {article.category or 'n/a'}",
            f"Enriched : {'yes' if article.is_enriched else 'no'}",
            f"URL      : {article.url}",
            "",
            "Description:",
            article.description or "(none)",
        ]
        if article.content_full:
            lines += ["", "Scraped content:", article.content_full]

        self._detail.config(state=tk.NORMAL)
        self._detail.delete("1.0", tk.END)
        self._detail.insert(tk.END, "\n".join(lines))
        self._detail.config(state=tk.DISABLED)
        self._open_btn.config(state=tk.NORMAL)

    def _open_in_browser(self) -> None:
        """Open the selected article's URL in the default web browser."""
        selection = self._listbox.curselection()
        if selection:
            webbrowser.open(self._articles[selection[0]].url)

    def _render_charts(self) -> None:
        """Rebuild the Charts tab from the latest aggregation result."""
        # Remove whatever charts were drawn last time.
        for widget in self._charts_tab.winfo_children():
            widget.destroy()
        if not self._articles:
            return

        # Two charts stacked vertically: by source and over time.
        fig_source = self._chart_builder.bar_by_source(
            self._aggregator.stats_by_source()
        )
        fig_time = self._chart_builder.timeline(self._articles)

        for fig in (fig_source, fig_time):
            canvas = FigureCanvasTkAgg(fig, master=self._charts_tab)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, pady=4)

    # ---------- Lifecycle ----------
    def run(self) -> None:
        """Start the Tkinter event loop (blocks until the window closes)."""
        self.root.mainloop()