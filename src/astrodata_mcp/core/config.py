"""Configuration: service endpoints and defaults."""
from __future__ import annotations

import os
from pathlib import Path

# Verified-working TAP endpoints (see docs/HANDOFF.md for quirks).
ENDPOINTS = {
    "eso_obs": "https://archive.eso.org/tap_obs",   # raw frames (dbo.raw) + Phase3 (ivoa.ObsCore)
    "eso_cat": "https://archive.eso.org/tap_cat",    # catalogues incl. GES_DR5_1_V1
    "gaia": "https://gea.esac.esa.int/tap-server/tap",
    "simbad": "https://simbad.cds.unistra.fr/simbad/sim-tap",
    "vizier": "https://tapvizier.cds.unistra.fr/TAPVizieR/tap",
    "koa": "https://koa.ipac.caltech.edu/TAP",  # Keck Observatory Archive (NExScI)
}

# Keck instruments exposed as one TAP table each (M5 crawlers).
KOA_INSTRUMENT_TABLES = {
    "HIRES": "koa_hires",
    "KCWI": "koa_kcwi",
}

# ESO secondary instruments reachable through the main tap_obs endpoint
# (raw: dbo.raw.instrument; reduced: ivoa.ObsCore.instrument_name).
ESO_SECONDARY_INSTRUMENTS = ("HARPS", "ESPRESSO", "UVES")

# Gaia-ESO final parameter/abundance catalogue (must be quoted in ADQL).
GES_TABLE = '"GES_DR5_1_V1"'

DEFAULT_MAX_ROWS_INLINE = 50
DEFAULT_TIMEOUT = 120  # seconds

# Where large results spill to disk.
OUTPUT_DIR = Path(
    os.environ.get("ASTRODATA_MCP_OUTDIR", str(Path.home() / "astrodata_mcp_out"))
)
