"""Magellan (Las Campanas) public-data crawler -- VizieR-backed (M5).

Reality check (verified 2026-06-25): unlike ESO and Keck, the Magellan
Telescopes have NO mandatory public raw-frame science archive with a VO / TAP
interface. Data are PI-owned (Carnegie + university consortium) and there is no
queryable equivalent of dbo.raw or koa_hires. A registry sweep for a Magellan /
Las Campanas TAP service returns nothing.

The public-data-only path (Decision of record, 2026-06-24) for Magellan
instruments (MIKE, MagE, PFS, IMACS) is therefore the set of PUBLISHED catalogs
derived from that data, which are curated in VizieR (radial velocities,
abundances, SB2 orbits, metal-poor samples). This module surfaces those via the
existing VizieR federation rather than inventing a raw-frame endpoint that does
not exist. It is honest about the limitation in every return payload.
"""
from __future__ import annotations

from . import vizier

# Phrases that bias a free-text catalog search toward Magellan instruments.
_INSTRUMENT_HINTS = ("MIKE", "MagE", "PFS", "IMACS", "Magellan")

_NO_RAW_NOTE = (
    "Magellan has no public raw-frame TAP archive (PI-owned data). Results are "
    "PUBLISHED VizieR catalogs derived from Magellan instruments, not raw frames."
)


def magellan_find_catalogs(keywords: str = "", max_catalogs: int = 20) -> dict:
    """Find published Magellan-instrument catalogs in VizieR.

    'keywords' is added to a Magellan-instrument context (MIKE / MagE / PFS).
    Use this to locate radial-velocity, abundance, or SB2-orbit tables built
    from Magellan spectra, then cone-search one with magellan_cone_search.
    """
    query = ("Magellan " + keywords).strip()
    res = vizier.vizier_find_catalogs(query, max_catalogs)
    res["note"] = _NO_RAW_NOTE
    res["instrument_hints"] = list(_INSTRUMENT_HINTS)
    return res


def magellan_cone_search(
    catalog: str,
    ra: float,
    dec: float,
    radius_arcsec: float = 60.0,
    limit: int = 50,
) -> dict:
    """Cone-search a specific Magellan-derived VizieR catalog at a position.

    'catalog' is a VizieR identifier from magellan_find_catalogs
    (e.g. 'J/AJ/152/167'). Returns published rows (RVs, abundances, orbits).

    Note: VizieR cone search needs the catalog to expose standard coordinate
    columns. Many RV time-series tables do not, so an empty result here does
    NOT mean the catalog is irrelevant -- read it directly with vizier_query
    or astroquery if the cone is empty (a hint is added to the payload).
    """
    res = vizier.vizier_query(catalog, ra, dec, radius_arcsec, limit)
    res["note"] = _NO_RAW_NOTE
    if res.get("n_rows", 0) == 0:
        res["fallback"] = (
            f"No cone match in '{catalog}'. The catalog may lack VizieR-standard "
            "coordinate columns (common for RV time-series); read the table "
            "directly rather than positionally, or confirm the position is in "
            "its footprint."
        )
    return res
