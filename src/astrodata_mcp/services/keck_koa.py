"""Keck Observatory Archive (KOA) crawler -- public data only.

KOA is hosted by NExScI and exposes one TAP table per instrument at
https://koa.ipac.caltech.edu/TAP (verified 2026-06-25; 14 instrument tables).
We wrap two instruments: HIRES (high-resolution echelle) and KCWI
(integral-field). Position columns are 'ra'/'dec' in degrees; cone search uses
ADQL CONTAINS. No login is needed for the metadata query: KOA serves all
archived header metadata publicly, and the proprietary period only gates the
pixel download (which this server does not do).
"""
from __future__ import annotations

from ..core.adql import cone_clause, quote
from ..core.config import ENDPOINTS, KOA_INSTRUMENT_TABLES
from ..core.query import tap_query
from ..core.results import format_result
from ..core.schema import list_columns

# Core, instrument-agnostic columns present in every koa_* table.
_KOA_COLS = (
    "koaid, targname, koaimtyp, ra, dec, date_obs, elaptime, "
    "progid, progpi, semester"
)


def _resolve_table(instrument: str) -> str:
    inst = instrument.upper()
    if inst not in KOA_INSTRUMENT_TABLES:
        raise ValueError(
            f"unsupported KOA instrument {instrument!r}; "
            f"choose one of {sorted(KOA_INSTRUMENT_TABLES)}"
        )
    return KOA_INSTRUMENT_TABLES[inst]


def koa_query(
    instrument: str = "HIRES",
    target: str | None = None,
    ra: float | None = None,
    dec: float | None = None,
    radius_arcsec: float | None = None,
    date_after: str | None = None,
    date_before: str | None = None,
    imagetyp: str | None = None,
    prog_id: str | None = None,
    limit: int = 50,
) -> dict:
    """Discover archived Keck frames for one instrument (HIRES or KCWI).

    Filter by target name, sky position (ra/dec deg + radius_arcsec), UTC date
    range (date_obs, 'YYYY-MM-DD'), image type (koaimtyp: 'object', 'bias',
    'flat', 'arclamp', ...), or program id prefix. Returns metadata only.
    """
    table = _resolve_table(instrument)
    where: list[str] = []
    if target:
        where.append(f"targname LIKE '%{quote(target)}%'")
    if imagetyp:
        where.append(f"koaimtyp = '{quote(imagetyp)}'")
    if prog_id:
        where.append(f"progid LIKE '{quote(prog_id)}%'")
    if date_after:
        where.append(f"date_obs > '{quote(date_after)}'")
    if date_before:
        where.append(f"date_obs < '{quote(date_before)}'")
    if ra is not None and dec is not None and radius_arcsec:
        where.append(cone_clause(ra, dec, radius_arcsec))
    clause = " AND ".join(where) if where else "1 = 1"
    query = (
        f"SELECT TOP {limit} {_KOA_COLS} FROM {table} "
        f"WHERE {clause} ORDER BY date_obs DESC"
    )
    res = tap_query(ENDPOINTS["koa"], query, label="koa", source="KOA")
    res["instrument"] = instrument.upper()
    res["archive"] = "Keck KOA"
    return res


def koa_schema(instrument: str = "HIRES") -> dict:
    """List the full column set of a KOA instrument table (FITS-header wide)."""
    table = _resolve_table(instrument)
    return format_result(
        list_columns(ENDPOINTS["koa"], table), max_rows=2000, label="koa_schema",
        source="KOA", endpoint=ENDPOINTS["koa"],
    )
