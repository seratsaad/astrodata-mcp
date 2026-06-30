"""Offline unit tests for the ADQL clause builders (no network).

Runs as a plain script, matching tests/test_smoke.py.
"""
from __future__ import annotations

import math

from astrodata_mcp.core.adql import bbox_clause, cone_clause, quote


def test_quote_escapes_single_quote():
    assert quote("Barnard's Star") == "Barnard''s Star"
    # A value with no quote is unchanged.
    assert quote("HD 122563") == "HD 122563"
    # Multiple quotes are each doubled.
    assert quote("a'b'c") == "a''b''c"


def test_quote_makes_literal_safe():
    # The built predicate must contain the doubled quote, never a lone one that
    # would terminate the literal early.
    target = "Barnard's Star"
    clause = f"object LIKE '%{quote(target)}%'"
    assert clause == "object LIKE '%Barnard''s Star%'"
    # Stripping the doubled quotes, no single quote should remain inside.
    inner = clause[len("object LIKE '%"):-len("%'")]
    assert "'" not in inner.replace("''", "")


def test_cone_clause_shape():
    c = cone_clause(10.0, 20.0, 3600.0)  # 1 degree radius
    assert "CONTAINS(POINT('ICRS', ra, dec)" in c
    assert "CIRCLE('ICRS', 10.0, 20.0, 1.0)" in c
    assert c.endswith("= 1")


def test_cone_clause_custom_columns():
    c = cone_clause(1.0, 2.0, 7200.0, "s_ra", "s_dec")
    assert "POINT('ICRS', s_ra, s_dec)" in c
    assert "CIRCLE('ICRS', 1.0, 2.0, 2.0)" in c


def test_bbox_clause_is_superset_of_cone():
    # The box half-widths must circumscribe the cone: dec half-width = r, ra
    # half-width = r / cos(dec) >= r.
    ra, dec, r_arcsec = 30.0, 60.0, 3600.0
    r = r_arcsec / 3600.0
    c = bbox_clause(ra, dec, r_arcsec)
    cosd = math.cos(math.radians(dec))
    assert f"dec BETWEEN {dec - r} AND {dec + r}" in c
    assert f"ra BETWEEN {ra - r / cosd} AND {ra + r / cosd}" in c
    # ra span is wider than dec span at non-zero dec.
    assert (r / cosd) > r


def test_bbox_clause_custom_columns():
    c = bbox_clause(5.0, -10.0, 3600.0, "RA", "DECLINATION")
    assert "RA BETWEEN" in c and "DECLINATION BETWEEN" in c


if __name__ == "__main__":
    for fn in (test_quote_escapes_single_quote, test_quote_makes_literal_safe,
               test_cone_clause_shape, test_cone_clause_custom_columns,
               test_bbox_clause_is_superset_of_cone,
               test_bbox_clause_custom_columns):
        fn()
        print(f"PASS {fn.__name__}")
    print("ALL ADQL TESTS PASSED")
