"""ESO secondary-instrument crawler -- HARPS / ESPRESSO / UVES (M5).

These instruments are already reachable through the main ESO TAP endpoint
(`tap_obs`); this module is a thin, instrument-validated convenience layer over
it so an agent can pull external high-resolution SB2 comparison spectra without
hand-writing ADQL. Two data tiers:

  - raw    : dbo.raw           (instrument = 'HARPS' | 'ESPRESSO' | 'UVES')
  - reduced: ivoa.ObsCore      (instrument_name = ..., dataproduct_type='spectrum')

UVES reduced spectra live mostly under the GAIAESO Phase 3 collection plus
several PI collections; raw UVES is in dbo.raw like the others. All public.
"""
from __future__ import annotations

from ..core.adql import bbox_clause, cone_clause, quote
from ..core.config import ENDPOINTS, ESO_SECONDARY_INSTRUMENTS
from ..core.query import tap_query


def _check_instrument(instrument: str) -> str:
    inst = instrument.upper()
    if inst not in ESO_SECONDARY_INSTRUMENTS:
        raise ValueError(
            f"unsupported ESO secondary instrument {instrument!r}; "
            f"choose one of {list(ESO_SECONDARY_INSTRUMENTS)}"
        )
    return inst


def eso_secondary_query(
    instrument: str,
    ra: float | None = None,
    dec: float | None = None,
    radius_arcsec: float | None = None,
    target: str | None = None,
    data_type: str = "reduced",
    limit: int = 50,
) -> dict:
    """Find HARPS / ESPRESSO / UVES data at a position or for a target.

    data_type='reduced' (default) returns Phase 3 1-D spectra (ivoa.ObsCore);
    data_type='raw' returns raw frames (dbo.raw). Filter by sky position
    (ra/dec deg + radius_arcsec) and/or target name.
    """
    inst = _check_instrument(instrument)
    where: list[str] = []

    if data_type == "raw":
        where.append(f"instrument = '{inst}'")
        if target:
            where.append(f"object LIKE '%{quote(target)}%'")
        if ra is not None and dec is not None and radius_arcsec:
            # dbo.raw CONTAINS triggers the ESO SqlGeography bug; bounding box.
            where.append(bbox_clause(ra, dec, radius_arcsec))
        query = (
            f"SELECT TOP {limit} dp_id, instrument, object, ra, dec, "
            "exposure, tpl_start, dp_cat, prog_id "
            f"FROM dbo.raw WHERE {' AND '.join(where)} ORDER BY tpl_start DESC"
        )
    elif data_type == "reduced":
        where.append(f"instrument_name = '{inst}'")
        where.append("dataproduct_type = 'spectrum'")
        if target:
            where.append(f"target_name LIKE '%{quote(target)}%'")
        if ra is not None and dec is not None and radius_arcsec:
            where.append(cone_clause(ra, dec, radius_arcsec, "s_ra", "s_dec"))
        query = (
            f"SELECT TOP {limit} obs_collection, instrument_name, target_name, "
            "s_ra, s_dec, em_min, em_max, t_exptime, access_url "
            f"FROM ivoa.ObsCore WHERE {' AND '.join(where)}"
        )
    else:
        raise ValueError(
            f"data_type must be 'reduced' or 'raw', got {data_type!r}"
        )

    res = tap_query(ENDPOINTS["eso_obs"], query, label="eso_secondary", source="ESO")
    res["instrument"] = inst
    res["data_type"] = data_type
    res["archive"] = "ESO"
    return res
