"""WeasyPrint-backed HTML → PDF rendering."""

from __future__ import annotations

from pathlib import Path

from weasyprint import HTML


def render_pdf(html: str, base_url: str | Path | None = None) -> bytes:
    """Render an HTML string into PDF bytes."""
    base = str(base_url) if base_url else None
    return HTML(string=html, base_url=base).write_pdf()
