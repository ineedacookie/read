"""
Lightweight query profiling utilities.

Only active when ``DEBUG`` is True to avoid any production overhead.
"""

from __future__ import annotations

import functools
import logging
import time
from contextlib import contextmanager

from django.conf import settings
from django.db import connection, reset_queries

logger = logging.getLogger("read.query")


@contextmanager
def query_debugger(label: str = "query_debugger"):
    """
    Context manager that logs SQL query counts and total time while the
    wrapped block executes. No-ops outside DEBUG mode.
    """

    if not settings.DEBUG:
        yield
        return

    reset_queries()
    start = time.perf_counter()
    try:
        yield
    finally:
        duration = (time.perf_counter() - start) * 1000  # ms
        queries = connection.queries
        total_time = sum(float(q.get("time", 0)) for q in queries) * 1000
        logger.debug(
            "%s executed %s SQL queries in %.1f ms (DB time %.1f ms)",
            label,
            len(queries),
            duration,
            total_time,
        )


def log_query_stats(label: str):
    """
    Decorator wrapper around :func:`query_debugger`.

    Example::

        @log_query_stats("home_view")
        def home(request):
            ...
    """

    def decorator(func):
        if not settings.DEBUG:
            return func

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with query_debugger(label):
                return func(*args, **kwargs)

        return wrapper

    return decorator


__all__ = ["query_debugger", "log_query_stats"]


