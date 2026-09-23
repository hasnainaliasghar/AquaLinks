"""Web search tool for the Historian agent.

Uses **Tavily** (https://tavily.com) when ``TAVILY_API_KEY`` is
configured — it returns pre-summarised, AI-ready content with relevance
scores, ideal for LLM agents.

Falls back to **DuckDuckGo** (``duckduckgo-search`` package, no key
required) when Tavily is not configured.

Both backends return the same schema so the Historian's tool-calling
code is backend-agnostic.
"""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

LOGGER = get_logger(__name__)

MAX_RESULTS_HARD_CAP = 8


def web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """Search the web and return structured results.

    Prefers Tavily when ``TAVILY_API_KEY`` is set; falls back to
    DuckDuckGo otherwise.

    Parameters
    ----------
    query:
        Natural-language query, e.g.
        ``"algal bloom Lake Victoria water quality 2024"``.
    max_results:
        How many results to return (1–8).

    Returns
    -------
    dict with:
        ``count``    — number of results returned.
        ``backend``  — ``"tavily"`` or ``"duckduckgo"``.
        ``results``  — list of {title, url, snippet}.
        ``error``    — present only on failure.
    """
    max_results = max(1, min(int(max_results), MAX_RESULTS_HARD_CAP))
    settings = get_settings()

    if settings.tavily_api_key:
        return _tavily_search(query, max_results, settings.tavily_api_key)
    return _ddg_search(query, max_results)


# ---------------------------------------------------------------------------
# Tavily backend
# ---------------------------------------------------------------------------


def _tavily_search(query: str, max_results: int, api_key: str) -> dict[str, Any]:
    """Search via Tavily API — returns pre-summarised, scored results."""
    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced",  # deeper crawl, better summaries
            include_answer=False,
        )
        raw_results = response.get("results") or []
        results = [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", r.get("raw_content", ""))[:800],
                "score": round(float(r.get("score", 0.0)), 3),
            }
            for r in raw_results
        ]
        LOGGER.debug("Tavily search for %r returned %d results", query, len(results))
        return {"count": len(results), "backend": "tavily", "results": results}

    except ImportError:
        LOGGER.warning("tavily-python not installed; falling back to DuckDuckGo")
        return _ddg_search(query, max_results)
    except Exception as exc:
        LOGGER.warning("Tavily search failed (%s); falling back to DuckDuckGo", exc)
        return _ddg_search(query, max_results)


# ---------------------------------------------------------------------------
# DuckDuckGo fallback backend
# ---------------------------------------------------------------------------


def _ddg_search(query: str, max_results: int) -> dict[str, Any]:
    """Search via DuckDuckGo — no API key required."""
    try:
        from duckduckgo_search import DDGS

        raw = DDGS().text(query, max_results=max_results)
        results = [
            {
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
            }
            for r in (raw or [])
        ]
        LOGGER.debug("DuckDuckGo search for %r returned %d results", query, len(results))
        return {"count": len(results), "backend": "duckduckgo", "results": results}

    except ImportError:
        LOGGER.error(
            "Neither tavily-python nor duckduckgo-search is installed. "
            "Add at least one to requirements.txt."
        )
        return {
            "count": 0,
            "backend": "none",
            "results": [],
            "error": "no search backend installed",
        }
    except Exception as exc:
        LOGGER.warning("DuckDuckGo search failed for query %r: %s", query, exc)
        return {
            "count": 0,
            "backend": "duckduckgo",
            "results": [],
            "error": f"{type(exc).__name__}: {exc}",
        }


__all__ = ["web_search"]
