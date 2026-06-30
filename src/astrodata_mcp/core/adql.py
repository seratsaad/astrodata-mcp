"""Small ADQL clause builders shared across services.

Two positional-filter styles, picked per endpoint:

- `cone_clause`: ADQL CONTAINS(POINT, CIRCLE), the precise geometry filter.
  Works on Gaia, SIMBAD, KOA, and ESO `ivoa.ObsCore`.
- `bbox_clause`: a RA/DEC bounding box. Use it where CONTAINS is unsupported or
  buggy. The ESO `dbo.raw` (and `tap_cat`) backends choke on CONTAINS with a
  server-side SqlGeography error (".NET ... Latitude values must be between -90
  and 90 degrees") regardless of the actual dec; a bounding box sidesteps the
  geography routine entirely. The box circumscribes the cone, so it is a
  superset (no false negatives; a few corner false positives) -- fine for
  frame/catalog discovery.
"""
from __future__ import annotations

import math


def quote(value: str) -> str:
    """Escape a string for safe use inside an ADQL single-quoted literal.

    ADQL/SQL escapes a single quote by doubling it. Without this, a value such
    as "Barnard's Star" breaks the query (and is a string-injection vector).
    Returns the inner text only -- the caller still wraps it in quotes, e.g.
    f"object LIKE '%{quote(target)}%'".
    """
    return str(value).replace("'", "''")


def cone_clause(
    ra: float, dec: float, radius_arcsec: float,
    ra_col: str = "ra", dec_col: str = "dec",
) -> str:
    """ADQL CONTAINS cone-search predicate (precise)."""
    r = radius_arcsec / 3600.0
    return (
        f"CONTAINS(POINT('ICRS', {ra_col}, {dec_col}), "
        f"CIRCLE('ICRS', {ra}, {dec}, {r})) = 1"
    )


def bbox_clause(
    ra: float, dec: float, radius_arcsec: float,
    ra_col: str = "ra", dec_col: str = "dec",
) -> str:
    """RA/DEC bounding-box predicate circumscribing the cone (geometry-free).

    Use where CONTAINS is unsupported or triggers the ESO SqlGeography bug.
    """
    r = radius_arcsec / 3600.0
    cosd = max(math.cos(math.radians(dec)), 1e-3)
    return (
        f"{ra_col} BETWEEN {ra - r / cosd} AND {ra + r / cosd} "
        f"AND {dec_col} BETWEEN {dec - r} AND {dec + r}"
    )
