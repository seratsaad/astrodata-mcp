"""Gaia service: ESA Gaia DR3 cone search, ADQL, and single-source lookup."""
from __future__ import annotations

from ..core.adql import cone_clause
from ..core.config import ENDPOINTS
from ..core.results import format_result
from ..core.tap import run_adql

_SOURCE_COLS = (
    "source_id, ra, dec, parallax, parallax_error, pmra, pmdec, "
    "phot_g_mean_mag, bp_rp, radial_velocity"
)


def gaia_cone_search(
    ra: float, dec: float, radius_arcsec: float = 5.0, limit: int = 50
) -> dict:
    """Cone search Gaia DR3 (gaiadr3.gaia_source) around a sky position."""
    query = (
        f"SELECT TOP {limit} {_SOURCE_COLS} FROM gaiadr3.gaia_source "
        f"WHERE {cone_clause(ra, dec, radius_arcsec)}"
    )
    return format_result(run_adql(ENDPOINTS["gaia"], query), label="gaia_cone")


def gaia_source(source_id: int) -> dict:
    """Look up a single Gaia DR3 source by source_id."""
    query = (
        f"SELECT {_SOURCE_COLS} FROM gaiadr3.gaia_source "
        f"WHERE source_id = {int(source_id)}"
    )
    return format_result(run_adql(ENDPOINTS["gaia"], query), label="gaia_source")


def gaia_adql(query: str) -> dict:
    """Run an arbitrary ADQL query against the Gaia TAP service."""
    return format_result(run_adql(ENDPOINTS["gaia"], query), label="gaia_adql")
