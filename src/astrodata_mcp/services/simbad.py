"""SIMBAD service: object name resolution via SIMBAD TAP."""
from __future__ import annotations

from ..core.config import ENDPOINTS
from ..core.results import format_result
from ..core.tap import run_adql


def simbad_resolve(name: str) -> dict:
    """Resolve an object identifier to coordinates and basic properties.

    Works for catalogue IDs and common names (HD, HIP, Gaia DR3, 2MASS, etc.).
    """
    safe = name.replace("'", "''")
    query = (
        "SELECT b.main_id, b.ra, b.dec, b.otype_txt, b.sp_type, "
        "b.plx_value, b.pmra, b.pmdec, b.rvz_radvel, b.nbref "
        "FROM basic AS b JOIN ident AS i ON b.oid = i.oidref "
        f"WHERE i.id = '{safe}'"
    )
    return format_result(run_adql(ENDPOINTS["simbad"], query), label="simbad_resolve")


def simbad_adql(query: str) -> dict:
    """Run an arbitrary ADQL query against the SIMBAD TAP service."""
    return format_result(run_adql(ENDPOINTS["simbad"], query), label="simbad_adql")
