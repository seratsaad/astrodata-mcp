"""VizieR service: catalogue discovery and cone search (via astroquery)."""
from __future__ import annotations

import astropy.units as u
from astropy.coordinates import SkyCoord
from astroquery.vizier import Vizier

from ..core.citations import CITATIONS, vizier_cite_path
from ..core.results import format_result


def vizier_find_catalogs(keywords: str, max_catalogs: int = 20) -> dict:
    """Search VizieR for catalogues matching keywords."""
    cats = Vizier.find_catalogs(keywords)
    items = [
        {"name": name, "description": getattr(meta, "description", "")}
        for name, meta in list(cats.items())[:max_catalogs]
    ]
    return {
        "n_catalogs": len(cats), "showing": len(items), "catalogs": items,
        "citation": CITATIONS["VizieR"],
    }


def vizier_query(
    catalog: str,
    ra: float,
    dec: float,
    radius_arcsec: float = 60.0,
    limit: int = 50,
) -> dict:
    """Cone search a specific VizieR catalogue around a sky position."""
    v = Vizier(row_limit=limit)
    coord = SkyCoord(ra=ra * u.deg, dec=dec * u.deg)
    result = v.query_region(coord, radius=radius_arcsec * u.arcsec, catalog=catalog)
    if not result or len(result) == 0:
        out = {"n_rows": 0, "columns": [], "rows": [], "truncated": False}
    else:
        out = format_result(result[0], label="vizier")
    out["provenance"] = {
        "service": "VizieR (astroquery.query_region)",
        "catalog": catalog,
        "ra": ra, "dec": dec, "radius_arcsec": radius_arcsec,
    }
    out["citation"] = CITATIONS["VizieR"]
    out["cite_source_paper"] = vizier_cite_path(catalog)
    return out
