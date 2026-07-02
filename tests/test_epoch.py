"""Offline tests for proper-motion / epoch propagation (no network).

Uses Barnard's Star (one of the highest-proper-motion stars known) as a case
with a large, checkable expected shift. Runs as a plain script.
"""
from __future__ import annotations

import math

from astrodata_mcp.core.epoch import propagate

# Barnard's Star, Gaia DR3 values (position at J2016.0).
BARNARD = dict(
    ra=269.4520769, dec=4.6933489,
    pmra=-801.551, pmdec=10362.394, parallax=546.976,
)


def test_barnard_shift_matches_pm_over_16yr():
    # Propagate J2016.0 -> J2000.0 (16 years). Expected total motion is
    # roughly |pm| * dt: sqrt(pmra^2 + pmdec^2) * 16 yr / 1000 mas -> arcsec.
    r = propagate(
        BARNARD["ra"], BARNARD["dec"], BARNARD["pmra"], BARNARD["pmdec"],
        from_epoch=2016.0, to_epoch=2000.0, parallax=BARNARD["parallax"],
    )
    expected = math.hypot(BARNARD["pmra"], BARNARD["pmdec"]) * 16.0 / 1000.0
    assert 150.0 < r["shift_arcsec"] < 180.0
    assert abs(r["shift_arcsec"] - expected) < 5.0  # ~166 arcsec
    assert r["from_epoch"] == 2016.0 and r["to_epoch"] == 2000.0


def test_zero_pm_does_not_move():
    r = propagate(150.0, 20.0, 0.0, 0.0, from_epoch=2016.0, to_epoch=2000.0)
    assert r["shift_arcsec"] < 1e-6
    assert abs(r["ra"] - 150.0) < 1e-9 and abs(r["dec"] - 20.0) < 1e-9


def test_round_trip_returns_to_start():
    fwd = propagate(
        BARNARD["ra"], BARNARD["dec"], BARNARD["pmra"], BARNARD["pmdec"],
        2016.0, 2000.0, parallax=BARNARD["parallax"],
    )
    back = propagate(
        fwd["ra"], fwd["dec"], BARNARD["pmra"], BARNARD["pmdec"],
        2000.0, 2016.0, parallax=BARNARD["parallax"],
    )
    # Back at ~2016.0 position (within a few mas).
    assert abs(back["ra"] - BARNARD["ra"]) < 1e-3
    assert abs(back["dec"] - BARNARD["dec"]) < 1e-3


if __name__ == "__main__":
    for fn in (test_barnard_shift_matches_pm_over_16yr,
               test_zero_pm_does_not_move,
               test_round_trip_returns_to_start):
        fn()
        print(f"PASS {fn.__name__}")
    print("ALL EPOCH TESTS PASSED")
