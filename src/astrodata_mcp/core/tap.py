"""Shared TAP client (pyvo) with caching and retry/backoff.

Using pyvo (VOTable over the wire) sidesteps the per-service FORMAT quirks
(e.g. tap_cat rejecting csv) we hit when querying by hand.

Failure handling (caveat C-MCP-1): archive endpoints intermittently drop the
connection, time out, or return an HTML rate-limit / error page instead of a
VOTable. pyvo surfaces those as DALServiceError (HTTP-level, incl. 5xx / 429),
DALFormatError (unparseable / HTML body), or a requests RequestException. We
retry those with exponential backoff so a transient hiccup does not turn into a
silently empty result. A DALQueryError is the server understanding the query and
rejecting it (ADQL syntax, the dbo.raw geometry bug, ...): that is deterministic,
so we do NOT retry it -- we raise immediately with the endpoint in the message.
"""
from __future__ import annotations

import time

import pyvo
from astropy.table import Table
from pyvo.dal.exceptions import (
    DALFormatError,
    DALQueryError,
    DALServiceError,
)
from requests.exceptions import RequestException

# Simple in-process TTL cache for repeated identical queries.
_CACHE: dict[tuple, tuple[float, Table]] = {}
_TTL_SECONDS = 900  # 15 minutes

# Retry policy for transient transport / formatting failures.
_MAX_ATTEMPTS = 3
_BACKOFF_BASE = 1.5  # seconds; sleep is _BACKOFF_BASE * 2**attempt

# Transient: worth retrying. DALQueryError is excluded on purpose (deterministic).
_RETRYABLE = (DALServiceError, DALFormatError, RequestException)


class TAPQueryError(RuntimeError):
    """A TAP query failed (after retries) or was rejected by the server."""


def run_adql(
    endpoint: str,
    query: str,
    maxrec: int | None = None,
    use_cache: bool = True,
) -> Table:
    """Run an ADQL query against a TAP endpoint and return an astropy Table.

    Identical (endpoint, query, maxrec) calls are cached for 15 minutes.
    Transient transport failures are retried with exponential backoff; a
    server-side query rejection (or exhausted retries) raises TAPQueryError.
    """
    key = (endpoint, query, maxrec)
    now = time.time()
    if use_cache and key in _CACHE:
        ts, table = _CACHE[key]
        if now - ts < _TTL_SECONDS:
            return table

    service = pyvo.dal.TAPService(endpoint)
    last_exc: Exception | None = None
    table: Table | None = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            table = service.search(query, maxrec=maxrec).to_table()
            break
        except DALQueryError as exc:
            # The server parsed and rejected the query: retrying repeats it.
            raise TAPQueryError(
                f"TAP query rejected by {endpoint}: {exc}"
            ) from exc
        except _RETRYABLE as exc:
            last_exc = exc
            if attempt < _MAX_ATTEMPTS - 1:
                time.sleep(_BACKOFF_BASE * (2 ** attempt))
    if table is None:
        raise TAPQueryError(
            f"TAP query to {endpoint} failed after {_MAX_ATTEMPTS} attempts "
            f"(last error: {last_exc}). The service may be rate-limiting, "
            "returning an error page, or temporarily down."
        ) from last_exc

    if use_cache:
        _CACHE[key] = (now, table)
    return table


def clear_cache() -> None:
    """Clear the query cache."""
    _CACHE.clear()
