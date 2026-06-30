"""Result handling: keep small results inline, spill large ones to disk."""
from __future__ import annotations

from typing import Any

import numpy as np
from astropy.table import Table

from .config import DEFAULT_MAX_ROWS_INLINE, OUTPUT_DIR


def _py(value: Any) -> Any:
    """Coerce numpy/masked scalars to JSON-serializable Python types."""
    if value is None or value is np.ma.masked:
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if np.isnan(value) else float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value


def _rows(table: Table, n: int) -> list[dict]:
    cols = table.colnames
    return [
        {c: _py(table[c][i]) for c in cols}
        for i in range(min(n, len(table)))
    ]


def format_result(
    table: Table,
    max_rows: int = DEFAULT_MAX_ROWS_INLINE,
    label: str = "result",
) -> dict:
    """Return a context-safe summary of a query result.

    Small results are returned inline. Large results spill to a parquet file
    and only a preview + path are returned.
    """
    n = len(table)
    out: dict = {"n_rows": n, "columns": list(table.colnames)}
    if n <= max_rows:
        out["rows"] = _rows(table, n)
        out["truncated"] = False
    else:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUTPUT_DIR / f"{label}.parquet"
        try:
            table.to_pandas().to_parquet(path)
            out["saved_to"] = str(path)
        except Exception as exc:  # pragma: no cover - disk/format issues
            out["save_error"] = str(exc)
        out["rows"] = _rows(table, max_rows)
        out["truncated"] = True
        out["note"] = f"Showing first {max_rows} of {n} rows; full table saved to disk."
    return out
