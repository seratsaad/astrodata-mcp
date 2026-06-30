# astrodata-mcp

[![tests](https://github.com/seratsaad/astrodata-mcp/actions/workflows/tests.yml/badge.svg)](https://github.com/seratsaad/astrodata-mcp/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An [MCP](https://modelcontextprotocol.io) server for querying astronomical
archives. It turns common archive lookups into read-only tools that any
MCP-compatible AI client (Claude Desktop, Claude Code, Cursor, or your own
agent) can call. Public data only, no credentials needed.

## Archives covered

- **ESO Science Archive** — raw frames, Phase 3 reduced products, catalogues
- **ESO secondary instruments** — HARPS, ESPRESSO, UVES
- **Keck Observatory Archive (KOA)** — HIRES, KCWI
- **Gaia DR3**
- **SIMBAD** — name resolution
- **VizieR** — published catalogues
- **Magellan** — published catalogues (MIKE / MagE / PFS) via VizieR

## Tools

| Group | Tools |
|---|---|
| ESO | `eso_raw_query`, `eso_phase3_query`, `eso_schema`, `find_raw_frames` |
| ESO secondary | `eso_secondary_query` (HARPS / ESPRESSO / UVES) |
| Keck KOA | `koa_query`, `koa_schema` |
| Gaia DR3 | `gaia_cone_search`, `gaia_source`, `gaia_adql` |
| SIMBAD | `simbad_resolve`, `simbad_adql` |
| VizieR | `vizier_find_catalogs`, `vizier_query` |
| Magellan | `magellan_find_catalogs`, `magellan_cone_search` |
| Cross-service | `crossmatch`, `resolve_and_enrich` |

All tools are read-only. Large results are capped inline and spilled to a
Parquet file (path returned).

## Install

```bash
git clone https://github.com/seratsaad/astrodata-mcp
cd astrodata-mcp
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e .
```

Requires Python 3.11+.

## Connect an MCP client

The server speaks MCP over stdio, so any MCP client works. Point your client
at the installed `astrodata-mcp` command. For Claude Desktop, add to
`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "astrodata": { "command": "/absolute/path/to/.venv/bin/astrodata-mcp" }
  }
}
```

Restart the client; the tools appear (in Claude they are named
`mcp__astrodata__*`).

## Usage

Ask your AI client in natural language; it picks the tools. For example:

> "Resolve HD 122563, then show nearby Gaia DR3 and any Keck HIRES data."

The client calls `simbad_resolve` for coordinates, then `crossmatch` and
`koa_query` at that position. Common patterns the tools map to:

- Resolve a target: `simbad_resolve("HD 122563")`
- Raw frames: `eso_raw_query(instrument="GIRAFFE", prog_id="188.B-3002")` or by
  position `eso_raw_query(ra=..., dec=..., radius_arcsec=...)`
- Reduced spectra: `eso_phase3_query(collection="GAIAESO")`,
  `eso_secondary_query("HARPS", ra=..., dec=...)`, `koa_query(instrument="HIRES", ra=..., dec=...)`
- Catalogues: `vizier_find_catalogs("...")` then `vizier_query(catalog, ra, dec)`

Large results are capped inline and spilled to a Parquet file (path returned).

## Optional extras

A few domain-specific tools (Gaia-ESO catalogue helpers and stellar follow-up
search) are kept out of the default set. Enable them by setting an environment
variable before launching the server:

```bash
ASTRODATA_MCP_EXTRAS=1
```

See `src/astrodata_mcp/extras.py`.

## Tests

```bash
python tests/test_smoke.py        # live: hits the real archives
python tests/test_adql.py         # offline
python tests/test_tap_retry.py    # offline
python tests/test_validation.py   # offline
```

The offline suites run in CI on every push; the live smoke test hits the real
archives and is run manually.

## Development

See [`docs/HANDOFF.md`](docs/HANDOFF.md) for the architecture, the TAP-federation
pattern, how to add a new archive, and known caveats.

## License

MIT. See [`LICENSE`](LICENSE).
