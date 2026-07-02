"""Offline result-parsing tests using a recorded VOTable (no network).

The live smoke tests exercise the parsing path against real services; this does
it deterministically from a saved VOTable response, so CI catches parsing
regressions (type coercion, NaN/masked handling, provenance/citation) without a
network. tests/fixtures/gaia_cone.vot was recorded from a Gaia-shaped response
and includes a NaN cell and a masked cell on purpose.
"""
from __future__ import annotations

import os

from astropy.table import Table

from astrodata_mcp.core import tap
from astrodata_mcp.core.results import format_result
from astrodata_mcp.services import gaia

_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "gaia_cone.vot")


def _load():
    return Table.read(_FIXTURE, format="votable")


def test_format_result_coerces_and_annotates():
    out = format_result(
        _load(), label="t", source="Gaia",
        adql="SELECT ...", endpoint="https://example/tap",
    )
    assert out["n_rows"] == 2
    assert out["truncated"] is False
    assert "source_id" in out["columns"]
    # Big int64 survives as a Python int.
    assert out["rows"][0]["source_id"] == 4472832130942575872
    # NaN -> None, masked -> None (context-safe JSON).
    assert out["rows"][1]["phot_g_mean_mag"] is None
    assert out["rows"][1]["parallax"] is None
    # Provenance + citation attached.
    assert out["provenance"] == {"endpoint": "https://example/tap", "adql": "SELECT ..."}
    assert "Gaia" in out["citation"]


def test_gaia_service_path_offline(monkeypatch):
    # Route the service's run_adql through the recorded table: exercises the full
    # gaia_cone_search formatting path (epoch + citation + provenance) offline.
    monkeypatch.setattr(tap, "run_adql", lambda *a, **k: _load())
    # gaia imports tap_query, which calls tap.run_adql via the core.query module.
    from astrodata_mcp.core import query as qmod
    monkeypatch.setattr(qmod, "run_adql", lambda *a, **k: _load())
    out = gaia.gaia_cone_search(269.45, 4.69, 30.0)
    assert out["n_rows"] == 2
    assert out["epoch"] == "J2016.0"
    assert "provenance" in out and out["provenance"]["endpoint"].endswith("/tap")
    assert "Gaia" in out["citation"]


if __name__ == "__main__":
    # Minimal monkeypatch shim so this runs without pytest.
    class _MP:
        def __init__(self):
            self._undo = []

        def setattr(self, obj, name, val):
            self._undo.append((obj, name, getattr(obj, name)))
            setattr(obj, name, val)

        def undo(self):
            for obj, name, val in reversed(self._undo):
                setattr(obj, name, val)

    test_format_result_coerces_and_annotates()
    print("PASS test_format_result_coerces_and_annotates")
    mp = _MP()
    try:
        test_gaia_service_path_offline(mp)
        print("PASS test_gaia_service_path_offline")
    finally:
        mp.undo()
    print("ALL PARSING TESTS PASSED")
