"""Background-task abstraction.

The default implementation wraps FastAPI's ``BackgroundTasks``. The
``JobRunner`` protocol exists so a Redis/RQ worker can be substituted
without changing call sites.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from fastapi import BackgroundTasks


class JobRunner(Protocol):
    """Schedules a callable to execute after the current request returns."""

    def enqueue(self, fn: Callable[..., Any], /, *args: Any, **kwargs: Any) -> None: ...


class InProcessJobRunner:
    """Runs jobs through FastAPI ``BackgroundTasks``."""

    def __init__(self, background: BackgroundTasks) -> None:
        self._background = background

    def enqueue(self, fn: Callable[..., Any], /, *args: Any, **kwargs: Any) -> None:
        self._background.add_task(fn, *args, **kwargs)
