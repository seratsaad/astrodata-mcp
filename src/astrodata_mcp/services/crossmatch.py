"""Cross-service tools: unified positional crossmatch and resolve+enrich."""
from __future__ import annotations

from ..core.adql import bbox_clause, cone_clause
from ..core.config import ENDPOINTS, GES_TABLE
from ..core.results import format_result
from ..core.tap import run_adql
from .simbad import simbad_resolve


def crossmatch(ra: float, dec: float, radius_arcsec: float = 5.0) -> dict:
    """Positional crossmatch a sky point against SIMBAD, Gaia DR3, and GES.

    Returns the nearest match in each service within the given radius.
    """
    out: dict = {"query": {"ra": ra, "dec": dec, "radius_arcsec": radius_arcsec}}

    # SIMBAD (TAP supports ADQL geometry on basic.ra/dec)
    simbad_q = (
        "SELECT TOP 1 main_id, ra, dec, otype_txt, sp_type FROM basic "
        f"WHERE {cone_clause(ra, dec, radius_arcsec)}"
    )
    out["simbad"] = format_result(run_adql(ENDPOINTS["simbad"], simbad_q), label="xm_simbad")

    # Gaia DR3
    gaia_q = (
        "SELECT TOP 1 source_id, ra, dec, parallax, pmra, pmdec, phot_g_mean_mag "
        "FROM gaiadr3.gaia_source "
        f"WHERE {cone_clause(ra, dec, radius_arcsec)}"
    )
    out["gaia_dr3"] = format_result(run_adql(ENDPOINTS["gaia"], gaia_q), label="xm_gaia")

    # GES: bounding box (tap_cat geometry support is not assumed)
    ges_q = (
        f"SELECT TOP 5 OBJECT, RA, DECLINATION, TEFF, LOGG, FEH FROM {GES_TABLE} "
        f"WHERE {bbox_clause(ra, dec, radius_arcsec, 'RA', 'DECLINATION')}"
    )
    out["ges"] = format_result(run_adql(ENDPOINTS["eso_cat"], ges_q), label="xm_ges")

    return out


def resolve_and_enrich(name: str, radius_arcsec: float = 5.0) -> dict:
    """Resolve a name via SIMBAD, then enrich with Gaia DR3 and GES matches."""
    s = simbad_resolve(name)
    if s["n_rows"] == 0:
        return {"resolved": False, "name": name}
    row = s["rows"][0]
    ra, dec = row.get("ra"), row.get("dec")
    if ra is None or dec is None:
        return {"resolved": True, "simbad": row, "note": "no coordinates to enrich"}
    xm = crossmatch(ra, dec, radius_arcsec)
    return {
        "resolved": True,
        "simbad": row,
        "gaia_dr3": xm["gaia_dr3"],
        "ges": xm["ges"],
    }
