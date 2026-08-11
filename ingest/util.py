"""Small helpers shared across the fetch_*.py scripts."""

from __future__ import annotations

from typing import Callable, TypeVar

T = TypeVar("T")


def dedupe_by_key(items: list[T], key_fn: Callable[[T], tuple]) -> list[T]:
    """
    Drops duplicate items that share the same key, keeping the LAST
    occurrence for each key (later entries in an ENTSO-E response are
    presumed to be a more recent revision of the same interval).

    ENTSO-E's day-ahead/actual-generation/actual-load/flow documents can
    legitimately contain more than one <TimeSeries> covering the same
    timestamp for a zone (observed live: duplicate rows caused a Postgres
    "ON CONFLICT DO UPDATE command cannot affect row a second time" error,
    since a single INSERT ... ON CONFLICT batch can't update the same
    target row twice). Deduplicating before writing avoids that, and also
    keeps the CSV output free of exact-duplicate rows.
    """
    deduped: dict[tuple, T] = {}
    for item in items:
        deduped[key_fn(item)] = item
    if len(deduped) < len(items):
        print(f"Dropped {len(items) - len(deduped)} duplicate row(s) sharing the same (zone, timestamp, ...) key.")
    return list(deduped.values())
