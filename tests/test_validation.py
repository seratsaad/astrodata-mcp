"""Offline input-validation tests (no network).

These lock in the security contract: user-supplied instrument / table names are
rejected against an allow-list BEFORE any ADQL is built or sent, so an
unvalidated name can never reach a query. Runs as a plain script.
"""
from __future__ import annotations

from astrodata_mcp.services import eso_secondary, keck_koa


def _expect_valueerror(fn, label):
    try:
        fn()
    except ValueError:
        return
    raise AssertionError(f"{label}: expected ValueError, none raised")


def test_koa_rejects_unknown_instrument():
    _expect_valueerror(
        lambda: keck_koa.koa_query(instrument="BOGUS"), "koa_query"
    )
    # An unwrapped KOA table (real instrument, but not one we expose) is rejected.
    _expect_valueerror(
        lambda: keck_koa.koa_query(instrument="NIRSPEC"), "koa_query NIRSPEC"
    )
    _expect_valueerror(
        lambda: keck_koa.koa_schema("DEIMOS"), "koa_schema"
    )


def test_koa_accepts_known_instruments():
    # Resolution must NOT raise for the supported instruments (case-insensitive).
    assert keck_koa._resolve_table("hires") == "koa_hires"
    assert keck_koa._resolve_table("KCWI") == "koa_kcwi"


def test_eso_secondary_rejects_unknown_instrument():
    _expect_valueerror(
        lambda: eso_secondary.eso_secondary_query("BOGUS"), "eso_secondary inst"
    )
    # GIRAFFE is a real ESO instrument but not a "secondary" one we expose here.
    _expect_valueerror(
        lambda: eso_secondary.eso_secondary_query("GIRAFFE"), "eso_secondary GIRAFFE"
    )


def test_eso_secondary_rejects_bad_data_type():
    _expect_valueerror(
        lambda: eso_secondary.eso_secondary_query("HARPS", data_type="weird"),
        "eso_secondary data_type",
    )


if __name__ == "__main__":
    for fn in (test_koa_rejects_unknown_instrument,
               test_koa_accepts_known_instruments,
               test_eso_secondary_rejects_unknown_instrument,
               test_eso_secondary_rejects_bad_data_type):
        fn()
        print(f"PASS {fn.__name__}")
    print("ALL VALIDATION TESTS PASSED")
