"""MCP server exposing astronomical archive queries as tools.

Core tools (always registered) wrap the public TAP / VO services of ESO,
Gaia, SIMBAD, VizieR, the Keck Observatory Archive, and ESO secondary
instruments, plus a VizieR-backed Magellan path. All are read-only.

A small set of domain-specific extras (Gaia-ESO catalogue helpers and
stellar-binary follow-up tools) live in `extras.py` and are registered only
when the environment variable ASTRODATA_MCP_EXTRAS is set.
"""
from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from .services import crossmatch as xm
from .services import (
    eso,
    eso_secondary,
    gaia,
    keck_koa,
    magellan_archive,
    project,
    simbad,
    vizier,
)

mcp = FastMCP("astrodata")


# --- ESO archive -----------------------------------------------------------
@mcp.tool()
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
    """Discover raw frames in the ESO Science Archive (dbo.raw).

    Filter by instrument (e.g. 'GIRAFFE', 'UVES', 'HARPS'), program id prefix
    (e.g. '188.B-3002'), target name, sky position (ra/dec in deg +
    radius_arcsec), observation date range, or data category
    ('SCIENCE'/'CALIB'/'ACQUISITION').
    """
    return eso.eso_raw_query(
        instrument, prog_id, target, ra, dec, radius_arcsec,
        date_after, date_before, category, limit,
    )


@mcp.tool()
def eso_phase3_query(
    collection: str | None = None,
    target: str | None = None,
    ra: float | None = None,
    dec: float | None = None,
    radius_arcsec: float | None = None,
    limit: int = 50,
) -> dict:
    """Discover processed (Phase 3) data products via ivoa.ObsCore.

    Filter by collection (e.g. 'GAIAESO', 'HARPS'), target, or sky position.
    """
    return eso.eso_phase3_query(collection, target, ra, dec, radius_arcsec, limit)


@mcp.tool()
def eso_schema(table: str, service: str = "obs") -> dict:
    """List columns of an ESO table. service='obs' (tap_obs) or 'cat' (tap_cat)."""
    return eso.eso_schema(table, service)


# --- SIMBAD ----------------------------------------------------------------
@mcp.tool()
def simbad_resolve(name: str) -> dict:
    """Resolve an object identifier (HD, HIP, Gaia DR3, 2MASS, common name)
    to coordinates, object type, spectral type, parallax, proper motion, RV."""
    return simbad.simbad_resolve(name)


@mcp.tool()
def simbad_adql(query: str) -> dict:
    """Run an arbitrary ADQL query against the SIMBAD TAP service."""
    return simbad.simbad_adql(query)


# --- Gaia DR3 --------------------------------------------------------------
@mcp.tool()
def gaia_cone_search(
    ra: float, dec: float, radius_arcsec: float = 5.0, limit: int = 50
) -> dict:
    """Cone search Gaia DR3 around a sky position (ra/dec in degrees)."""
    return gaia.gaia_cone_search(ra, dec, radius_arcsec, limit)


@mcp.tool()
def gaia_source(source_id: int) -> dict:
    """Look up a single Gaia DR3 source by source_id."""
    return gaia.gaia_source(source_id)


@mcp.tool()
def gaia_adql(query: str) -> dict:
    """Run an arbitrary ADQL query against the Gaia TAP service."""
    return gaia.gaia_adql(query)


# --- VizieR ----------------------------------------------------------------
@mcp.tool()
def vizier_find_catalogs(keywords: str, max_catalogs: int = 20) -> dict:
    """Search VizieR for catalogues matching keywords."""
    return vizier.vizier_find_catalogs(keywords, max_catalogs)


@mcp.tool()
def vizier_query(
    catalog: str, ra: float, dec: float, radius_arcsec: float = 60.0, limit: int = 50
) -> dict:
    """Cone search a specific VizieR catalogue around a sky position."""
    return vizier.vizier_query(catalog, ra, dec, radius_arcsec, limit)


# --- Keck Observatory Archive ----------------------------------------------
@mcp.tool()
def koa_query(
    instrument: str = "HIRES",
    target: str | None = None,
    ra: float | None = None,
    dec: float | None = None,
    radius_arcsec: float | None = None,
    date_after: str | None = None,
    date_before: str | None = None,
    imagetyp: str | None = None,
    prog_id: str | None = None,
    limit: int = 50,
) -> dict:
    """Discover public Keck frames (instrument='HIRES' or 'KCWI') in the Keck
    Observatory Archive. Filter by target, sky position (ra/dec deg +
    radius_arcsec), date range, image type ('object'/'bias'/'flat'/'arclamp'),
    or program id. Metadata only (no proprietary pixel access)."""
    return keck_koa.koa_query(
        instrument, target, ra, dec, radius_arcsec,
        date_after, date_before, imagetyp, prog_id, limit,
    )


@mcp.tool()
def koa_schema(instrument: str = "HIRES") -> dict:
    """List the columns of a KOA instrument table ('HIRES' or 'KCWI')."""
    return keck_koa.koa_schema(instrument)


# --- ESO secondary instruments (HARPS / ESPRESSO / UVES) -------------------
@mcp.tool()
def eso_secondary_query(
    instrument: str,
    ra: float | None = None,
    dec: float | None = None,
    radius_arcsec: float | None = None,
    target: str | None = None,
    data_type: str = "reduced",
    limit: int = 50,
) -> dict:
    """Find HARPS / ESPRESSO / UVES data via ESO TAP. data_type='reduced'
    (Phase 3 1-D spectra) or 'raw' (dbo.raw frames). Filter by sky position
    (ra/dec deg + radius_arcsec) and/or target name."""
    return eso_secondary.eso_secondary_query(
        instrument, ra, dec, radius_arcsec, target, data_type, limit,
    )


# --- Magellan (VizieR-backed; no public raw archive) -----------------------
@mcp.tool()
def magellan_find_catalogs(keywords: str = "", max_catalogs: int = 20) -> dict:
    """Find published Magellan-instrument (MIKE/MagE/PFS) catalogs in VizieR.
    Magellan has no public raw-frame TAP archive; this surfaces literature
    tables (RVs, abundances, orbits) derived from Magellan spectra."""
    return magellan_archive.magellan_find_catalogs(keywords, max_catalogs)


@mcp.tool()
def magellan_cone_search(
    catalog: str, ra: float, dec: float,
    radius_arcsec: float = 60.0, limit: int = 50,
) -> dict:
    """Cone-search a Magellan-derived VizieR catalog (id from
    magellan_find_catalogs, e.g. 'J/AJ/152/167') at a sky position."""
    return magellan_archive.magellan_cone_search(
        catalog, ra, dec, radius_arcsec, limit
    )


# --- Cross-service ---------------------------------------------------------
@mcp.tool()
def crossmatch(ra: float, dec: float, radius_arcsec: float = 5.0) -> dict:
    """Positional crossmatch a sky point against SIMBAD and Gaia DR3 (plus the
    public Gaia-ESO catalogue); returns the nearest match in each."""
    return xm.crossmatch(ra, dec, radius_arcsec)


@mcp.tool()
def resolve_and_enrich(name: str, radius_arcsec: float = 5.0) -> dict:
    """Resolve an object name via SIMBAD, then enrich with Gaia DR3 (and
    Gaia-ESO catalogue) matches at its position."""
    return xm.resolve_and_enrich(name, radius_arcsec)


# --- ESO programs ----------------------------------------------------------
@mcp.tool()
def find_raw_frames(
    prog_id: str, run: str | None = None, instrument: str | None = None,
    category: str = "SCIENCE",
) -> dict:
    """Summarize raw frames for an ESO program (counts + GB by
    instrument/category). e.g. prog_id='188.B-3002', run='A'."""
    return project.find_raw_frames(prog_id, run, instrument, category)


# --- Optional domain-specific extras (opt-in) ------------------------------
# Enable with ASTRODATA_MCP_EXTRAS=1 to add the Gaia-ESO catalogue helpers and
# stellar-binary follow-up tools defined in extras.py.
if os.environ.get("ASTRODATA_MCP_EXTRAS", "").strip().lower() in (
    "1", "true", "yes", "on"
):
    from . import extras

    extras.register(mcp)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
