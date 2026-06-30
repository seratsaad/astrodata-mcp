"""ESO archive service: raw-frame discovery, Phase3 spectra, GES catalogue."""
from __future__ import annotations

from ..core.adql import bbox_clause, cone_clause, quote
from ..core.config import ENDPOINTS, GES_TABLE
from ..core.results import format_result
from ..core.schema import list_columns
from ..core.tap import run_adql


def eso_raw_query(
    instrument: str | None = None,
    prog_id: str | None = None,
    target: str | None = None,
    ra: float | None = None,
    dec: float | None = None,
    radius_arcsec: float | None = None,
    date_after: str | None = None,
    date_before: str | None = None,
    category: str | None = None,
    limit: int = 50,
) -> dict:
    """Discover raw frames in the ESO SAF (dbo.raw)."""
    where: list[str] = []
    if instrument:
        where.append(f"instrument = '{quote(instrument)}'")
    if prog_id:
        where.append(f"prog_id LIKE '{quote(prog_id)}%'")
    if target:
        where.append(f"object LIKE '%{quote(target)}%'")
    if category:
        where.append(f"dp_cat = '{quote(category)}'")
    if date_after:
        where.append(f"tpl_start > '{quote(date_after)}'")
    if date_before:
        where.append(f"tpl_start < '{quote(date_before)}'")
    if ra is not None and dec is not None and radius_arcsec:
        # dbo.raw CONTAINS cone search triggers the ESO SqlGeography bug; use a
        # RA/DEC bounding box (superset of the cone) instead. See core/adql.py.
        where.append(bbox_clause(ra, dec, radius_arcsec))
    clause = " AND ".join(where) if where else "1 = 1"
    query = (
        f"SELECT TOP {limit} dp_id, instrument, prog_id, object, ra, dec, "
        "exposure, tpl_start, dp_cat, access_estsize "
        f"FROM dbo.raw WHERE {clause} ORDER BY tpl_start DESC"
    )
    return format_result(run_adql(ENDPOINTS["eso_obs"], query), label="eso_raw")


def eso_phase3_query(
    collection: str | None = None,
    target: str | None = None,
    ra: float | None = None,
    dec: float | None = None,
    radius_arcsec: float | None = None,
    limit: int = 50,
) -> dict:
    """Discover processed (Phase 3) data products via ivoa.ObsCore."""
    where: list[str] = []
    if collection:
        where.append(f"obs_collection = '{quote(collection)}'")
    if target:
        where.append(f"target_name LIKE '%{quote(target)}%'")
    if ra is not None and dec is not None and radius_arcsec:
        # ivoa.ObsCore supports CONTAINS fine (different backend from dbo.raw).
        where.append(cone_clause(ra, dec, radius_arcsec, "s_ra", "s_dec"))
    clause = " AND ".join(where) if where else "1 = 1"
    query = (
        f"SELECT TOP {limit} obs_collection, dataproduct_type, target_name, "
        "s_ra, s_dec, em_min, em_max, access_url "
        f"FROM ivoa.ObsCore WHERE {clause}"
    )
    return format_result(run_adql(ENDPOINTS["eso_obs"], query), label="eso_phase3")


def ges_query(adql: str | None = None, limit: int = 50) -> dict:
    """Query the Gaia-ESO final catalogue (GES_DR5_1_V1).

    Pass a full ADQL string, or omit it for a preview of the table.
    """
    query = adql or f"SELECT TOP {limit} * FROM {GES_TABLE}"
    return format_result(run_adql(ENDPOINTS["eso_cat"], query), label="ges")


def eso_schema(table: str, service: str = "obs") -> dict:
    """List columns of an ESO table. service: 'obs' (tap_obs) or 'cat' (tap_cat)."""
    endpoint = ENDPOINTS["eso_cat"] if service == "cat" else ENDPOINTS["eso_obs"]
    return format_result(list_columns(endpoint, table), max_rows=500, label="eso_schema")
