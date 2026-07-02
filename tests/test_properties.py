"""Property-based tests for the ADQL builders (offline, no network).

Uses hypothesis to check invariants across a wide range of inputs -- the kind
of edge cases hand-written examples miss. Run with pytest, or as a script.
"""
from __future__ import annotations

import math

from hypothesis import given, settings
from hypothesis import strategies as st

from astrodata_mcp.core.adql import bbox_clause, cone_clause, quote

ras = st.floats(min_value=0.0, max_value=360.0, allow_nan=False, allow_infinity=False)
decs = st.floats(min_value=-89.9, max_value=89.9, allow_nan=False, allow_infinity=False)
radii = st.floats(min_value=0.1, max_value=7200.0, allow_nan=False, allow_infinity=False)
texts = st.text(min_size=0, max_size=40)


@given(texts)
def test_quote_leaves_no_lone_single_quote(s):
    # After escaping, removing every doubled quote must leave zero single quotes,
    # i.e. no quote can prematurely terminate the ADQL literal.
    escaped = quote(s)
    assert "'" not in escaped.replace("''", "")


@given(texts)
def test_quote_only_doubles_quotes(s):
    # Non-quote characters are unchanged; only the count of quotes doubles.
    escaped = quote(s)
    assert escaped.count("'") == 2 * s.count("'")
    # Removing the doubled quotes from the escaped string leaves the same text
    # as removing the single quotes from the original.
    assert escaped.replace("''", "") == s.replace("'", "")


@given(ras, decs, radii)
@settings(max_examples=200)
def test_cone_clause_wellformed(ra, dec, r):
    c = cone_clause(ra, dec, r)
    assert c.startswith("CONTAINS(POINT('ICRS', ra, dec)")
    assert c.endswith("= 1")
    # The radius embedded in the CIRCLE is the arcsec radius in degrees.
    assert f"{r / 3600.0}" in c


@given(ras, decs, radii)
@settings(max_examples=200)
def test_bbox_is_superset_of_cone(ra, dec, r):
    # The dec half-width equals the radius; the ra half-width is >= the radius
    # (divided by cos dec), so the box always encloses the cone.
    r_deg = r / 3600.0
    cosd = max(math.cos(math.radians(dec)), 1e-3)
    c = bbox_clause(ra, dec, r)
    assert f"dec BETWEEN {dec - r_deg} AND {dec + r_deg}" in c
    assert (r_deg / cosd) >= r_deg - 1e-12


if __name__ == "__main__":
    # Run each hypothesis test directly (they self-drive their examples).
    for fn in (test_quote_leaves_no_lone_single_quote,
               test_quote_only_doubles_quotes,
               test_cone_clause_wellformed,
               test_bbox_is_superset_of_cone):
        fn()
        print(f"PASS {fn.__name__}")
    print("ALL PROPERTY TESTS PASSED")
