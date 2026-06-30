# astrodata-mcp passdown (2026-06-25)

Single handoff document for this archive-query MCP server. It states what the
project is, the current best version, what was tried and the design decisions
taken, what is next, and where everything lives. Written so a new AI agent (or
developer) can pick this up cold. Plain text only: no em-dash, no arrows, no
emoji.

---

## 1. What this project is

A general-purpose MCP server (FastMCP, stdio) that exposes public astronomical
archives as read-only tools any MCP-compatible AI client can call. It wraps the
public TAP / VO services of ESO (main archive and catalogues), Gaia DR3, SIMBAD,
VizieR, the Keck Observatory Archive, ESO secondary instruments (HARPS /
ESPRESSO / UVES), and a VizieR-backed Magellan path. No archive is
credential-gated: PUBLIC DATA ONLY. The server never downloads proprietary
pixels; it returns metadata, catalogue rows, and access URLs.

The 18 core tools are domain-agnostic. A small set of opt-in extras (Gaia-ESO
catalogue helpers and a stellar high-resolution follow-up search) live in
`extras.py` and load only when `ASTRODATA_MCP_EXTRAS=1` is set; they were built
for a Gaia-ESO / stellar-spectroscopy workflow and are kept available without
cluttering the general core.

---

## 2. Current best version (what to run)

18 core tools (always on) + 5 opt-in extras (23 total), all read-only,
registered in `src/astrodata_mcp/server.py`. Live smoke suite is 22/22 passing
(`tests/test_smoke.py`) plus 13 offline unit tests with no network: 3 retry
(`tests/test_tap_retry.py`) + 6 ADQL builder / quote-safety
(`tests/test_adql.py`) + 4 input validation (`tests/test_validation.py`).

Core (always registered):
| Group | Tools |
| --- | --- |
| ESO main | `eso_raw_query`, `eso_phase3_query`, `eso_schema`, `find_raw_frames` |
| ESO secondary | `eso_secondary_query` (HARPS / ESPRESSO / UVES, raw or reduced) |
| Keck KOA | `koa_query`, `koa_schema` |
| Gaia DR3 | `gaia_cone_search`, `gaia_source`, `gaia_adql` |
| SIMBAD | `simbad_resolve`, `simbad_adql` |
| VizieR | `vizier_find_catalogs`, `vizier_query` |
| Magellan | `magellan_find_catalogs`, `magellan_cone_search` (VizieR-backed) |
| Cross-service | `crossmatch`, `resolve_and_enrich` |

Extras (only with `ASTRODATA_MCP_EXTRAS=1`, defined in `extras.py`):
| Group | Tools |
| --- | --- |
| Gaia-ESO catalogue | `ges_query`, `ges_completeness`, `validate_against_ges` |
| Stellar follow-up | `crossmatch_external_sb2`, `find_followup_targets` |

Run and test:
```bash
cd ~/projects/astrodata-mcp
python3.11 -m venv .venv && source .venv/bin/activate   # already created
pip install -e .
python tests/test_smoke.py        # expect ALL SMOKE TESTS PASSED (22/22)
python -m astrodata_mcp           # the server itself (Claude Desktop launches it)
```
Python 3.11+ required (the `mcp` package needs >= 3.10; we use 3.11.15 at
`~/.local/bin/python3.11`). Registered in Claude Desktop under
`mcpServers.astrodata` in
`~/Library/Application Support/Claude/claude_desktop_config.json`; after a full
quit and reopen the tools appear as `mcp__astrodata__*`. A JSON backup of the
config was saved when the entry was first merged.

---

## 3. Architecture and the TAP-federation pattern

```
src/astrodata_mcp/
  server.py            # FastMCP app; core @mcp.tool() wrappers + opt-in extras
  extras.py            # opt-in domain tools (ASTRODATA_MCP_EXTRAS=1) -> register(mcp)
  core/
    tap.py             # shared pyvo TAP client: cache + retry/backoff (TAPQueryError)
    adql.py            # cone_clause / bbox_clause / quote (shared ADQL helpers)
    results.py         # context-safe: cap rows inline, spill big tables to parquet
    schema.py          # TAP_SCHEMA introspection (list_columns / list_tables)
    config.py          # ENDPOINTS map + KOA / ESO-secondary instrument tables
  services/
    eso.py             # raw (dbo.raw) / Phase3 (ivoa.ObsCore) / GES_DR5_1_V1
    simbad.py  gaia.py  vizier.py
    crossmatch.py      # multi-service positional join
    project.py         # find_raw_frames (core) + ges_completeness/validate (extras)
    keck_koa.py        # Keck Observatory Archive (koa_hires / koa_kcwi)
    eso_secondary.py   # HARPS / ESPRESSO / UVES via the main ESO endpoint
    magellan_archive.py# VizieR-backed published-catalog path (no raw archive)
    external.py        # extras backend: crossmatch_external_sb2 / find_followup_targets
tests/test_smoke.py    # live tests (22/22 pass)
tests/test_tap_retry.py # offline retry/backoff unit tests (3)
tests/test_adql.py      # offline ADQL builder + quote-safety tests (6)
tests/test_validation.py # offline allow-list / input-validation tests (4)
```

The pattern for every service: build an ADQL string, call
`core.tap.run_adql(endpoint, query)` (returns an astropy Table, cached 15 min by
(endpoint, query, maxrec)), then `core.results.format_result(table, label=...)`
which returns rows inline when small and spills to parquet when large. Endpoints
live in `core/config.py` `ENDPOINTS`. server.py wrappers exist only to give the
MCP schema clean argument names and docstrings; logic lives in the service.

### How to add a new archive (the recipe)
1. Add its TAP endpoint to `ENDPOINTS` in `core/config.py` (and any
   instrument-to-table map, as `KOA_INSTRUMENT_TABLES` shows).
2. Write `services/<name>.py` with one function per query shape. Build ADQL with
   `core.adql.cone_clause` (precise CONTAINS) or `bbox_clause` (geometry-free,
   for backends where CONTAINS is unsupported / buggy), call `run_adql`, wrap
   with `format_result`. Validate user-supplied instrument / table names against
   an allow-list (see `keck_koa._resolve_table`); never interpolate an
   unvalidated table name. Wrap any user STRING that goes inside an ADQL literal
   with `core.adql.quote` (target names, ids, dates) -- otherwise an apostrophe
   breaks the query. `run_adql` already retries transient failures and raises
   `TAPQueryError` on a hard failure -- do not add your own retry loop.
3. Add a thin `@mcp.tool()` wrapper in `server.py` and import the service at the
   top.
4. Add a live smoke test in `tests/test_smoke.py` with a target known to have
   archived data (probe first; positions used: 51 Peg for KOA HIRES, tau Ceti
   for ESO HARPS/ESPRESSO).
5. Probe the endpoint BEFORE writing code: list its tables, list a table's
   columns via `TAP_SCHEMA.columns`, and run one real cone search to learn the
   coordinate-column names and any quirks. Endpoints differ on FORMAT, geometry
   support, column casing.

---

## 4. Credential model

None. Public data only, by Decision of record (2026-06-24). No archive in this
server requires a login: KOA serves all archived header metadata publicly and
the proprietary period gates only the pixel download (which this server does not
perform); ESO main and catalogue TAP are open; Gaia / SIMBAD / VizieR are open.
If a future archive needs auth, that is a scope change requiring sign-off, not a
quiet addition.

---

## 5. M5 design decisions and what was tried

- KOA endpoint is `https://koa.ipac.caltech.edu/TAP` (verified 2026-06-25,
  14 instrument tables). We wrap `koa_hires` and `koa_kcwi`; HIRES is the SB2
  comparison workhorse. Position columns are plain `ra` / `dec` in degrees;
  cone search via ADQL CONTAINS works directly (unlike ESO `dbo.raw`, which
  needs the bounding-box workaround, see C-M5-2). The aliased `ra2000` /
  `dec2000` columns are NOT usable in POINT() (server rejects them) -- use
  `ra` / `dec`.
- ESO secondary (HARPS / ESPRESSO / UVES) is NOT a new endpoint: all three are
  reachable through the existing main `tap_obs` endpoint, raw in `dbo.raw`
  (instrument=...) and reduced 1-D spectra in `ivoa.ObsCore`
  (instrument_name=..., dataproduct_type='spectrum'). UVES reduced spectra live
  mostly under the GAIAESO Phase 3 collection. `eso_secondary.py` is a
  validated convenience layer over this, not a rebuild.
- Magellan has NO public raw-frame TAP archive (verified 2026-06-25; PI-owned
  Carnegie + university consortium data; a registry sweep returns nothing). The
  public-data-only path is therefore the PUBLISHED catalogs derived from
  Magellan instruments (MIKE / MagE / PFS / IMACS), curated in VizieR. The
  `magellan_archive.py` tools surface those via the existing VizieR federation
  and state the limitation in every return payload. We deliberately did NOT
  invent a raw-frame endpoint that does not exist. This is the "vendor API may
  be required where public TAP is thin" branch the plan anticipated; the honest
  resolution was VizieR, not a vendor API.
- `crossmatch_external_sb2(ra, dec)` reports Keck HIRES plus ESO
  HARPS/ESPRESSO/UVES (reduced) coverage at one point, for checking an SB2
  against archival comparison spectra. `find_followup_targets(ra, dec, ...)`
  cone-searches Gaia DR3 in a region and returns sources with NO external
  high-res coverage as follow-up candidates; it is bounded by
  `max_targets` (hard cap 25) because it runs per-target archive checks.

Verification done: 51 Peg returns Keck HIRES frames; tau Ceti returns ESO
HARPS/ESPRESSO reduced spectra; UVES raw bounding-box search returns frames;
Magellan catalogue discovery returns published tables; and >= 3 of four real
RV-monitored systems (51 Peg, tau Ceti, HD 209458, HD 80606) return non-empty
external high-res hits through the crawlers (`test_external_three_systems_nonempty`).

---

## 6. Caveats (running list)

- C-M5-1 (OPEN, low; bounded attempt made). The literal M5 verification target
  was ">= 3 of El-Badry+2018b's 64 orbital-solution systems." That catalogue
  (MNRAS 476, 528) was never ingested into VizieR: a `TAP_SCHEMA` search for
  `476/528` returns nothing, and a search for `El-Badry` returns only co-author
  matches on OTHER catalogues. A web search and a VizieR description search for
  the nearest published APOGEE SB2 / double-lined catalogues (e.g. Kounkel+2021)
  also failed to surface a machine-readable table with usable coordinates, and
  the VO registry is unreachable from this build environment (connection reset).
  We therefore verified the INTENT -- >= 3 real RV-monitored binary systems
  returning non-empty external high-res hits through the crawlers
  (`test_external_three_systems_nonempty`, with 51 Peg, tau Ceti, HD 209458,
  HD 80606). To close LITERALLY: drop the El-Badry+2018b orbital-solution table
  (paper supplement file or its VizieR code, once known) somewhere readable,
  feed its coordinates to `crossmatch_external_sb2`, confirm >= 3 hits. Low
  priority; the crawlers are already proven to return real archive data.
- C-M5-2 (FIXED 2026-06-25). ESO `dbo.raw` cone search via ADQL CONTAINS / POINT
  triggers a server-side SqlGeography bug (".NET Framework error ... Latitude
  values must be between -90 and 90 degrees") regardless of dec. Both
  `eso_raw_query` and `eso_secondary_query(data_type='raw')` now use a RA/DEC
  bounding box (`core.adql.bbox_clause`) instead of CONTAINS, which sidesteps the
  geography routine. Guarded by `test_eso_raw_cone_search` (the exact NGC2420
  reproducer that used to fail) and `test_eso_secondary_raw_bbox`. The precise
  CONTAINS path is kept (`core.adql.cone_clause`) for the backends that support
  it: Gaia, SIMBAD, KOA, and ESO `ivoa.ObsCore`. The bounding box is a superset
  of the cone (a few corner false positives), acceptable for frame discovery.
- C-M5-3 (MITIGATED 2026-06-25). `magellan_cone_search` depends on the specific
  VizieR catalogue exposing standard coordinate columns; some RV time-series
  tables do not, so a cone can return zero rows even when the catalogue is
  relevant. The tool now adds an explicit `fallback` hint to any empty result
  pointing the agent to read the table directly. Use `magellan_find_catalogs`
  to locate the table first.
- C-MCP-1 (FIXED 2026-06-25). Archive endpoints intermittently drop the
  connection, time out, or return an HTML rate-limit / error page; the shared
  client could then surface a confusing failure or (historically) an empty
  result. `core.tap.run_adql` now retries transient transport / format failures
  (DALServiceError, DALFormatError, requests RequestException) with exponential
  backoff and raises a clear `TAPQueryError` when retries are exhausted; a
  deterministic server rejection (DALQueryError: ADQL syntax, geometry) is NOT
  retried and raises immediately with the endpoint named. Offline coverage in
  `tests/test_tap_retry.py` (fake service; no network). Still open as a future
  refinement: per-tool error budgets and explicit HTML-body sniffing (pyvo
  currently catches HTML as a parse error, which is treated as retryable).
- C-M5-4 (FIXED 2026-06-25). User strings (target, prog_id, imagetyp, category,
  dates, collection) were interpolated raw into ADQL string literals, so a value
  with an apostrophe (e.g. "Barnard's Star") broke the query -- a correctness
  bug and a mild string-injection vector. `core.adql.quote` now doubles single
  quotes per the ADQL standard, and every service applies it at the
  interpolation site (eso, eso_secondary, keck_koa, project; simbad already did).
  Instrument / table names remain allow-listed (the stronger guard). The ADQL
  passthrough tools (`ges_query`, `gaia_adql`, `simbad_adql`) and the
  `ges_completeness(where=...)` predicate are intentionally raw agent-authored
  ADQL, not user-data interpolation, so they are left as-is. Offline coverage in
  `tests/test_adql.py`.
- C-M5-5 (OPEN, low; by design). `find_followup_targets` runs ~2N sequential
  archive checks (one Keck + one ESO per Gaia source), so latency grows with
  `max_targets` (hard-capped at 25, and the 15-min query cache helps on repeats).
  Acceptable for an interactive seed-list tool; if it ever needs to scan a large
  region, batch the per-target checks into a single ADQL `IN` / join instead.
- C-MCP-2 (OPEN, low). The VizieR-backed tools (`vizier_*`, `magellan_*`) call
  astroquery directly, so they do NOT pass through `core.tap.run_adql` and thus
  skip the retry/backoff added for C-MCP-1. astroquery has its own transport
  handling, but the behavior is inconsistent with the TAP path. Low priority;
  route them through a shared retry wrapper if VizieR flakiness shows up.
- C-M5-6 (AUDITED, no bug 2026-06-25). A possible ra/dec swap in cone search was
  flagged. Audited `core.adql` (POINT('ICRS', ra, dec) / CIRCLE('ICRS', ra, dec,
  r) -- RA first, Dec second, the correct ADQL convention) and all 11 call
  sites, then empirically confirmed every cone tool returns objects at the
  REQUESTED position at both a northern (51 Peg, ra=344) and southern (tau Ceti,
  dec=-15.9) target -- no swap. The smoke suite previously only asserted
  n_rows>=1, which would NOT catch a swap; `test_cone_positions_not_swapped` now
  asserts the nearest returned object is within the search radius (51 Peg is a
  strong discriminator: a swap makes dec=344, invalid, so a swapped query errors
  or returns nothing). Verified the guard fails on an injected swap. If you ever
  see wrong-position results, FIRST check that Claude Desktop was restarted to
  load the current build -- a stale server is the likeliest cause.

---

## 7. Where data, config, and verified numbers live

- Repo: `github.com/seratsaad/astrodata-mcp` (public).
- Large query results spill to `$ASTRODATA_MCP_OUTDIR` (default
  `~/astrodata_mcp_out`) as parquet; see `core/config.py`.
- MCP clients connect over stdio to the `astrodata-mcp` command; for Claude
  Desktop the config is `~/Library/Application Support/Claude/claude_desktop_config.json`.
- Regression anchors (do not let these drift silently): `GES_DR5_1_V1` row count
  = 114,916; `instrument='4MOST'` in `dbo.raw` = 0 (not yet public); KOA
  `koa_hires` and `koa_kcwi` present at the endpoint above.

---

## 8. Next promising directions

1. Close C-M5-1 literally once the El-Badry+2018b orbital table is in hand
   (drop the supplement file somewhere readable; the verification harness
   already exists in `crossmatch_external_sb2`).
2. Per-tool error BUDGET on top of the retry/backoff now in `core.tap` (C-MCP-1
   fixed the transport layer): explicit HTML-body sniffing and a small per-tool
   timeout / row cap policy if specific endpoints prove flaky in practice.
3. If a consumer repeatedly issues the same ad-hoc ADQL (e.g. Gaia
   `nss_two_body_orbit` or XP-spectra pulls), promote it to a dedicated tool.

---

## 9. Standing rules for anyone editing this repo

- Commits authored as `seratsaad <seratmahmudsaad@gmail.com>`. NO Claude
  attribution, NO Co-Authored-By trailers, NO emoji in code or messages.
- Prose docs (this file, README): plain text only, no em-dash, no arrows, no
  emoji, no non-Latin glyphs. Code may use arrows where they aid clarity.
- Update this file BEFORE any commit that changes user-facing behavior: add new
  caveats, mark fixed ones, keep the tool table and smoke-test count current
  (Standing practice 1.1 and 1.2). End each task by listing new caveats observed.
- Public data only. Adding a credential-gated archive is a scope change.
