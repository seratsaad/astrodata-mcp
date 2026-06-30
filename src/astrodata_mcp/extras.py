"""Optional, domain-specific tools (opt-in).

These are NOT part of the generic archive core. They were built for a
Gaia-ESO / stellar-spectroscopy workflow but are kept here for anyone who
wants them. They stay out of the default tool list so the core server is
general-purpose.

Enable by setting ASTRODATA_MCP_EXTRAS=1 (or true/yes/on) before launching
the server; `server.py` then calls `register(mcp)`.

Tools added:
  - ges_query              query the Gaia-ESO final catalogue (GES_DR5_1_V1)
  - ges_completeness       per-element completeness of that catalogue
  - validate_against_ges   compare a local parameter table to GES by position
  - crossmatch_external_sb2  external high-res spectroscopy coverage at a point
  - find_followup_targets    Gaia sources in a region lacking high-res coverage
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .services import eso, external, project


def register(mcp: FastMCP) -> None:
    """Register the optional domain-specific tools on the given MCP server."""

    @mcp.tool()
    def ges_query(adql: str | None = None, limit: int = 50) -> dict:
        """Query the Gaia-ESO final parameter/abundance catalogue (GES_DR5_1_V1).

        Pass a full ADQL string (table must be quoted: "GES_DR5_1_V1"), or omit
        for a preview. Use eso_schema('GES_DR5_1_V1', service='cat') for columns.
        """
        return eso.ges_query(adql, limit)

    @mcp.tool()
    def ges_completeness(where: str | None = None) -> dict:
        """Per-element completeness of the Gaia-ESO catalogue, optionally on a
        subset (e.g. where="SETUP LIKE '%U5%'" for UVES stars)."""
        return project.ges_completeness(where)

    @mcp.tool()
    def validate_against_ges(
        results_path: str, ra_col: str = "ra", dec_col: str = "dec",
        radius_arcsec: float = 3.0,
    ) -> dict:
        """Compare a local parameter table (.csv/.parquet with ra/dec + any of
        teff/logg/feh) to the Gaia-ESO catalogue by positional match; report
        residual stats."""
        return project.validate_against_ges(
            results_path, ra_col, dec_col, radius_arcsec
        )

    @mcp.tool()
    def crossmatch_external_sb2(
        ra: float, dec: float, radius_arcsec: float = 5.0
    ) -> dict:
        """At one sky point, report external high-resolution spectroscopy
        coverage (Keck HIRES + ESO HARPS/ESPRESSO/UVES reduced) for
        cross-checking a target against archival comparison spectra."""
        return external.crossmatch_external_sb2(ra, dec, radius_arcsec)

    @mcp.tool()
    def find_followup_targets(
        ra: float, dec: float, radius_arcmin: float = 10.0,
        mag_limit: float = 14.0, max_targets: int = 10,
    ) -> dict:
        """Find Gaia DR3 sources in a region (G < mag_limit) that lack external
        high-resolution spectra (Keck HIRES / ESO HARPS/ESPRESSO/UVES) --
        follow-up candidates. Bounded by max_targets (hard cap 25)."""
        return external.find_followup_targets(
            ra, dec, radius_arcmin, mag_limit, max_targets
        )
