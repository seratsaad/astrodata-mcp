"""Gaia service: ESA Gaia DR3 cone search, ADQL, and single-source lookup.

Positions are at the Gaia DR3 reference epoch J2016.0 (the `ref_epoch` column).
Cross-matching them against catalogues at other epochs drifts for high-proper-
motion stars; use `core.epoch.propagate` (or the crossmatch epoch handling) to
bring positions to a common epoch first.
"""
from __future__ import annotations

from ..core.adql import cone_clause
from ..core.config import ENDPOINTS
from ..core.query import tap_query

GAIA_DR3_EPOCH = 2016.0  # J2016.0; the ref_epoch of every Gaia DR3 position

_SOURCE_COLS = (
    "source_id, ra, dec, ref_epoch, parallax, parallax_error, pmra, pmdec, "
    "phot_g_mean_mag, bp_rp, radial_velocity"
)


def _with_epoch(result: dict) -> dict:
    result["epoch"] = "J2016.0"
    return result


def gaia_cone_search(
    ra: float, dec: float, radius_arcsec: float = 5.0, limit: int = 50
) -> dict:
    """Cone search Gaia DR3 (gaiadr3.gaia_source) around a sky position.

    Positions are at epoch J2016.0 (see `ref_epoch`)."""
    query = (
        f"SELECT TOP {limit} {_SOURCE_COLS} FROM gaiadr3.gaia_source "
        f"WHERE {cone_clause(ra, dec, radius_arcsec)}"
    )
    return _with_epoch(
        tap_query(ENDPOINTS["gaia"], query, label="gaia_cone", source="Gaia")
    )


def gaia_source(source_id: int) -> dict:
    """Look up a single Gaia DR3 source by source_id (position at J2016.0)."""
    query = (
        f"SELECT {_SOURCE_COLS} FROM gaiadr3.gaia_source "
        f"WHERE source_id = {int(source_id)}"
    )
    return _with_epoch(
        tap_query(ENDPOINTS["gaia"], query, label="gaia_source", source="Gaia")
    )


def gaia_adql(query: str) -> dict:
    """Run an arbitrary ADQL query against the Gaia TAP service."""
    return tap_query(ENDPOINTS["gaia"], query, label="gaia_adql", source="Gaia")
