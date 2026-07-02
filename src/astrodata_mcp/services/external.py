"""Backend for the optional external-archive federation tools (extras.py).

Two helpers that sit on top of the archive crawlers:

  - crossmatch_external_sb2: at one sky point, report what external high-
    resolution spectroscopy exists (Keck HIRES + ESO HARPS/ESPRESSO/UVES) so a
    target can be compared against literature-grade archival spectra.
  - find_followup_targets: in a region, find Gaia sources that do NOT yet have
    external high-resolution coverage -- candidates worth a follow-up.

These are registered only when ASTRODATA_MCP_EXTRAS is set; see extras.py.
"""
from __future__ import annotations

from ..core.adql import cone_clause
from ..core.citations import CITATIONS
from ..core.config import ENDPOINTS, ESO_SECONDARY_INSTRUMENTS
from ..core.query import tap_query
from ..core.tap import run_adql
from .keck_koa import koa_query


def _eso_secondary_hits(ra: float, dec: float, radius_arcsec: float, limit: int = 20):
    """Reduced HARPS/ESPRESSO/UVES spectra at a point (ivoa.ObsCore)."""
    inst_list = ", ".join(f"'{i}'" for i in ESO_SECONDARY_INSTRUMENTS)
    query = (
        f"SELECT TOP {limit} obs_collection, instrument_name, target_name, "
        "s_ra, s_dec, em_min, em_max, access_url "
        f"FROM ivoa.ObsCore WHERE instrument_name IN ({inst_list}) "
        "AND dataproduct_type = 'spectrum' "
        f"AND {cone_clause(ra, dec, radius_arcsec, 's_ra', 's_dec')}"
    )
    return tap_query(ENDPOINTS["eso_obs"], query, label="ext_eso", source="ESO")


def crossmatch_external_sb2(
    ra: float, dec: float, radius_arcsec: float = 5.0
) -> dict:
    """External high-resolution spectroscopy coverage at one sky point.

    Reports Keck HIRES and ESO HARPS/ESPRESSO/UVES (reduced) holdings near the
    position, for cross-checking an SB2 against archival comparison spectra.
    Magellan is catalog-only (no positional raw archive); use
    magellan_find_catalogs separately.
    """
    out: dict = {
        "query": {"ra": ra, "dec": dec, "radius_arcsec": radius_arcsec},
    }
    out["keck_hires"] = koa_query(
        instrument="HIRES", ra=ra, dec=dec, radius_arcsec=radius_arcsec, limit=20
    )
    out["eso_secondary"] = _eso_secondary_hits(ra, dec, radius_arcsec)
    out["has_external_highres"] = (
        out["keck_hires"]["n_rows"] > 0 or out["eso_secondary"]["n_rows"] > 0
    )
    out["note"] = (
        "Magellan (MIKE/MagE) is not positionally queryable; check published "
        "catalogs with magellan_find_catalogs if a southern comparison is needed."
    )
    return out


def find_followup_targets(
    ra: float,
    dec: float,
    radius_arcmin: float = 10.0,
    mag_limit: float = 14.0,
    max_targets: int = 10,
) -> dict:
    """Find Gaia sources in a region lacking external high-resolution spectra.

    Cone-searches Gaia DR3 (G < mag_limit), then for each source checks Keck
    HIRES and ESO HARPS/ESPRESSO/UVES coverage; returns those with NO external
    high-res spectra -- good follow-up candidates. Bounded by
    max_targets (hard cap 25) to keep the per-target archive checks cheap.
    """
    max_targets = min(int(max_targets), 25)
    r_deg = radius_arcmin / 60.0
    gaia_q = (
        f"SELECT TOP {max_targets} source_id, ra, dec, phot_g_mean_mag, "
        "parallax, bp_rp FROM gaiadr3.gaia_source "
        f"WHERE phot_g_mean_mag < {mag_limit} "
        f"AND CONTAINS(POINT('ICRS', ra, dec), "
        f"CIRCLE('ICRS', {ra}, {dec}, {r_deg})) = 1 "
        "ORDER BY phot_g_mean_mag ASC"
    )
    gaia = run_adql(ENDPOINTS["gaia"], gaia_q)

    candidates: list[dict] = []
    covered: list[dict] = []
    for row in gaia:
        sra, sdec = float(row["ra"]), float(row["dec"])
        koa_n = koa_query(
            instrument="HIRES", ra=sra, dec=sdec, radius_arcsec=3.0, limit=1
        )["n_rows"]
        eso_n = _eso_secondary_hits(sra, sdec, 3.0, limit=1)["n_rows"]
        entry = {
            "source_id": int(row["source_id"]),
            "ra": sra,
            "dec": sdec,
            "phot_g_mean_mag": float(row["phot_g_mean_mag"]),
            "keck_hires_frames": koa_n,
            "eso_secondary_spectra": eso_n,
        }
        if koa_n == 0 and eso_n == 0:
            candidates.append(entry)
        else:
            covered.append(entry)

    return {
        "query": {
            "ra": ra, "dec": dec, "radius_arcmin": radius_arcmin,
            "mag_limit": mag_limit, "max_targets": max_targets,
        },
        "n_searched": len(gaia),
        "n_followup_candidates": len(candidates),
        "n_already_covered": len(covered),
        "followup_candidates": candidates,
        "already_covered": covered,
        "note": (
            "Candidates have no Keck HIRES or ESO HARPS/ESPRESSO/UVES coverage "
            "within 3 arcsec. 'max_targets' caps the Gaia pull (and the per-"
            "target archive checks); raise it for a wider sweep."
        ),
        "provenance": {"endpoint": ENDPOINTS["gaia"], "adql": gaia_q},
        "citation": [CITATIONS["Gaia"], CITATIONS["KOA"], CITATIONS["ESO"]],
    }
