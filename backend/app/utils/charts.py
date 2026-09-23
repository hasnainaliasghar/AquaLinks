"""Inline-SVG chart helpers used by the PDF report."""

from __future__ import annotations

import io

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")

from app.models.spectral_index import IndexName

_INDEX_RANGES: dict[IndexName, tuple[float, float]] = {
    IndexName.NDWI: (-1.0, 1.0),
    IndexName.MNDWI: (-1.0, 1.0),
    IndexName.NDTI: (-1.0, 1.0),
    IndexName.NDCI: (-1.0, 1.0),
    IndexName.NDVI: (-1.0, 1.0),
    IndexName.WRI: (0.0, 3.0),
}


def index_bar_svg(name: IndexName, value: float) -> str:
    """Return an SVG bar chart visualising a single index value."""
    low, high = _INDEX_RANGES[name]
    fig, ax = plt.subplots(figsize=(3.6, 0.7), dpi=140)
    ax.barh(
        [0],
        [value - low],
        left=[low],
        color="#0ea5b7",
        height=0.5,
    )
    ax.set_xlim(low, high)
    ax.set_yticks([])
    ax.set_xticks([low, (low + high) / 2, high])
    ax.tick_params(axis="x", labelsize=7, colors="#52525b")
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color("#d4d4d8")
    ax.spines["bottom"].set_linewidth(0.5)
    ax.set_title(
        f"{name.value} · {value:+.3f}",
        loc="left",
        fontsize=9,
        color="#18181b",
        pad=4,
    )
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)
    return buf.getvalue()
