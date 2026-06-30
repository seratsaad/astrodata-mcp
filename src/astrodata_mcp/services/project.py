"""ESO program summary (core) and Gaia-ESO catalogue helpers (extras).

find_raw_frames is a core tool; ges_completeness and validate_against_ges back
the opt-in extras (see extras.py).
"""
from __future__ import annotations

import statistics

import pandas as pd

from ..core.adql import bbox_clause, quote
from ..core.config import ENDPOINTS, GES_TABLE
from ..core.results import format_result
from ..core.tap import run_adql

# Representative element spread (common -> rare) for completeness reporting.
DEFAULT_ELEMENTS = [
    "FEH", "NA1", "MG1", "AL1", "SI1", "CA1", "TI1", "CR1",
    "MN1", "NI1", "O1", "BA2", "Y2", "LA2", "EU2", "ND2",
]


def find_raw_frames(
    prog_id: str,
    run: str | None = None,
    instrument: str | None = None,
    category: str = "SCIENCE",
) -> dict:
    """Summarize raw frames for a program: counts + GB by instrument/category.

    prog_id e.g. '188.B-3002'; optional run letter e.g. 'A' selects one run.
    """
    if run:
        where = [f"prog_id = '{quote(prog_id)}({quote(run)})'"]
    else:
        where = [f"prog_id LIKE '{quote(prog_id)}%'"]
    if instrument:
        where.append(f"instrument = '{quote(instrument)}'")
    if category:
        where.append(f"dp_cat = '{quote(category)}'")
    query = (
        "SELECT instrument, dp_cat, count(*) AS n_frames, "
        "SUM(access_estsize)/1024.0/1024.0 AS gb "
        f"FROM dbo.raw WHERE {' AND '.join(where)} "
        "GROUP BY instrument, dp_cat ORDER BY gb DESC"
    )
    res = format_result(run_adql(ENDPOINTS["eso_obs"], query), label="find_raw_frames")
    res["note"] = (
        "Sizes cover the listed category only. Associated raw calibrations are "
        "tagged to separate calibration programs and add roughly 2-4x more "
        "volume (~3.6x observed for one Gaia-ESO run, science -> science+calib)."
    )
    return res


def ges_completeness(
    where: str | None = None, elements: list[str] | None = None
) -> dict:
    """Per-element completeness of the GES catalogue, optionally on a subset.

    'where' is an ADQL predicate, e.g. "SETUP LIKE '%U5%'" for UVES stars.
    """
    elements = elements or DEFAULT_ELEMENTS
    cols = ", ".join(f"count({e}) AS {e}" for e in elements)
    clause = f" WHERE {where}" if where else ""
    query = f"SELECT count(*) AS total, {cols} FROM {GES_TABLE}{clause}"
    table = run_adql(ENDPOINTS["eso_cat"], query)
    # TAP services may return aliases in lowercase; match case-insensitively.
    row = {c.lower(): table[c][0] for c in table.colnames}
    total = int(row["total"])
    out: dict = {"total": total, "where": where, "completeness": {}}
    for e in elements:
        val = row.get(e.lower())
        n = int(val) if val is not None else 0
        out["completeness"][e] = {
            "n": n,
            "pct": round(100.0 * n / total, 1) if total else None,
        }
    return out


def validate_against_ges(
    results_path: str,
    ra_col: str = "ra",
    dec_col: str = "dec",
    radius_arcsec: float = 3.0,
    max_rows: int = 500,
) -> dict:
    """Compare a pipeline's parameter table to GES by positional match.

    Reads a .csv or .parquet with columns including ra/dec (deg) and any of
    teff/logg/feh, matches each row to the nearest GES star within radius,
    and reports residual statistics (mine - GES) per parameter.
    """
    if results_path.endswith(".parquet"):
        df = pd.read_parquet(results_path)
    else:
        df = pd.read_csv(results_path)
    if len(df) > max_rows:
        return {
            "error": f"input has {len(df)} rows; cap is {max_rows}. "
            "Use a subset (TAP table upload is a future enhancement)."
        }

    param_map = {"teff": "TEFF", "logg": "LOGG", "feh": "FEH"}
    active = {m: g for m, g in param_map.items() if m in df.columns}
    residuals: dict[str, list[float]] = {m: [] for m in active}
    n_matched = 0

    for _, row in df.iterrows():
        ra, dec = float(row[ra_col]), float(row[dec_col])
        sel = ", ".join(["RA", "DECLINATION", *active.values()])
        query = (
            f"SELECT TOP 1 {sel} FROM {GES_TABLE} "
            f"WHERE {bbox_clause(ra, dec, radius_arcsec, 'RA', 'DECLINATION')}"
        )
        t = run_adql(ENDPOINTS["eso_cat"], query)
        if len(t) == 0:
            continue
        n_matched += 1
        for mine, ges in active.items():
            mv, gv = row[mine], t[ges][0]
            if pd.notna(mv) and gv is not None:
                residuals[mine].append(float(mv) - float(gv))

    stats: dict[str, dict] = {}
    for k, vals in residuals.items():
        if vals:
            stats[k] = {
                "n": len(vals),
                "mean": round(statistics.mean(vals), 3),
                "median": round(statistics.median(vals), 3),
                "std": round(statistics.pstdev(vals), 3) if len(vals) > 1 else 0.0,
            }
        else:
            stats[k] = {"n": 0}
    return {
        "input_rows": len(df),
        "matched": n_matched,
        "radius_arcsec": radius_arcsec,
        "residuals": stats,
    }
