"""Run an ADQL query and format it with provenance + citation in one step.

Centralises the common pattern so every TAP-backed tool returns the exact
query and endpoint it used (reproducibility) and the archive's required
acknowledgement (citation), without repeating the plumbing in each service.
"""
from __future__ import annotations

from .config import DEFAULT_MAX_ROWS_INLINE
from .results import format_result
from .tap import run_adql


def tap_query(
    endpoint: str,
    adql: str,
    *,
    label: str,
    source: str,
    maxrec: int | None = None,
    max_rows: int = DEFAULT_MAX_ROWS_INLINE,
) -> dict:
    """Execute `adql` against `endpoint` and return a formatted result dict
    carrying `provenance` (endpoint + adql) and `citation` (for `source`)."""
    table = run_adql(endpoint, adql, maxrec=maxrec)
    return format_result(
        table, max_rows=max_rows, label=label,
        source=source, adql=adql, endpoint=endpoint,
    )
