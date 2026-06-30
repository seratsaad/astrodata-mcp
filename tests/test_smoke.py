"""Live smoke tests (require network access to the TAP services)."""
from __future__ import annotations

import math
import os
import tempfile

import pandas as pd

from astrodata_mcp.services import (
    crossmatch,
    eso,
    eso_secondary,
    external,
    gaia,
    keck_koa,
    magellan_archive,
    project,
    simbad,
    vizier,
)

# Reference positions used by the M5 external-archive tests.
# 51 Peg (HD 217014): heavily HIRES-observed; tau Ceti (HD 10700): HARPS/ESPRESSO.
POS_51PEG = (344.3661, 20.7689)
POS_TAU_CET = (26.0170, -15.9374)


def _sep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    """Angular separation in arcsec (haversine)."""
    d2r = math.pi / 180.0
    a = (
        math.sin((dec2 - dec1) * d2r / 2) ** 2
        + math.cos(dec1 * d2r) * math.cos(dec2 * d2r)
        * math.sin((ra2 - ra1) * d2r / 2) ** 2
    )
    return 2 * math.asin(min(1.0, math.sqrt(a))) / d2r * 3600.0


def test_ges_count():
    res = eso.ges_query('SELECT count(*) AS n FROM "GES_DR5_1_V1"')
    assert res["n_rows"] == 1
    # The verified Gaia-ESO DR5.1 star count.
    n = res["rows"][0]
    assert list(n.values())[0] == 114916


def test_eso_raw_4most_absent():
    res = eso.eso_raw_query(instrument="4MOST", limit=1)
    assert res["n_rows"] == 0  # not yet released


def test_eso_raw_giraffe_gaiaeso():
    res = eso.eso_raw_query(instrument="GIRAFFE", prog_id="188.B-3002", limit=5)
    assert res["n_rows"] > 0


def test_eso_phase3_gaiaeso():
    res = eso.eso_phase3_query(collection="GAIAESO", limit=3)
    assert res["n_rows"] >= 1
    assert "obs_collection" in res["columns"]


def test_eso_raw_cone_search():
    # Regression guard for the dbo.raw SqlGeography bug: this exact call used to
    # fail server-side. Now uses a RA/DEC bounding box. NGC2420 field.
    res = eso.eso_raw_query(
        instrument="GIRAFFE", ra=114.61, dec=21.58,
        radius_arcsec=1500, category="SCIENCE", limit=5,
    )
    assert res["n_rows"] >= 1


def test_simbad_resolve():
    res = simbad.simbad_resolve("HD 122563")
    assert res["n_rows"] >= 1
    assert "ra" in res["columns"]


def test_gaia_cone_search():
    s = simbad.simbad_resolve("HD 122563")
    ra, dec = s["rows"][0]["ra"], s["rows"][0]["dec"]
    res = gaia.gaia_cone_search(ra, dec, radius_arcsec=10.0)
    assert res["n_rows"] >= 1
    assert "source_id" in res["columns"]


def test_resolve_and_enrich():
    res = crossmatch.resolve_and_enrich("HD 122563")
    assert res["resolved"] is True
    # Gaia DR3 should have a match near this bright benchmark star.
    assert res["gaia_dr3"]["n_rows"] >= 1


def test_ges_completeness():
    res = project.ges_completeness()
    assert res["total"] == 114916
    assert 75 <= res["completeness"]["FEH"]["pct"] <= 90  # ~82% verified


def test_find_raw_frames():
    res = project.find_raw_frames("188.B-3002", run="A")
    insts = {r["instrument"] for r in res["rows"]}
    assert "GIRAFFE" in insts or "UVES" in insts


def test_validate_against_ges():
    sel = eso.ges_query(
        'SELECT TOP 3 RA, DECLINATION, TEFF, LOGG, FEH FROM "GES_DR5_1_V1" '
        "WHERE TEFF IS NOT NULL AND FEH IS NOT NULL AND LOGG IS NOT NULL"
    )
    rows = [{k.lower(): v for k, v in r.items()} for r in sel["rows"]]
    df = pd.DataFrame(
        [{"ra": r["ra"], "dec": r["declination"], "teff": r["teff"],
          "logg": r["logg"], "feh": r["feh"]} for r in rows]
    )
    path = os.path.join(tempfile.mkdtemp(), "mine.csv")
    df.to_csv(path, index=False)
    out = project.validate_against_ges(path, radius_arcsec=2.0)
    assert out["matched"] >= 1
    # We fed GES's own values back, so residuals should be ~0.
    assert abs(out["residuals"]["teff"]["mean"]) < 5.0


def test_vizier_find_catalogs():
    res = vizier.vizier_find_catalogs("Gaia-ESO Survey")
    assert "n_catalogs" in res


# --- M5 crawler smoke tests ------------------------------------------------
def test_koa_hires_cone():
    ra, dec = POS_51PEG
    res = keck_koa.koa_query(
        instrument="HIRES", ra=ra, dec=dec, radius_arcsec=180, limit=5
    )
    assert res["n_rows"] >= 1
    assert "koaid" in res["columns"]
    assert res["archive"] == "Keck KOA"


def test_koa_schema():
    res = keck_koa.koa_schema("HIRES")
    cols = {r["column_name"] for r in res["rows"]}
    assert {"ra", "dec", "koaid"}.issubset(cols)


def test_eso_secondary_reduced():
    ra, dec = POS_TAU_CET
    res = eso_secondary.eso_secondary_query(
        "HARPS", ra=ra, dec=dec, radius_arcsec=180, data_type="reduced", limit=5
    )
    assert res["n_rows"] >= 1
    assert res["instrument"] == "HARPS"


def test_eso_secondary_raw_bbox():
    # Regression guard for the dbo.raw geography-bug workaround (bounding box).
    ra, dec = POS_TAU_CET
    res = eso_secondary.eso_secondary_query(
        "UVES", ra=ra, dec=dec, radius_arcsec=300, data_type="raw", limit=5
    )
    assert res["n_rows"] >= 1


def test_magellan_find_catalogs():
    res = magellan_archive.magellan_find_catalogs("metal-poor", max_catalogs=5)
    assert res["n_catalogs"] >= 1
    assert "no public raw-frame TAP" in res["note"]


def test_magellan_cone_search_note():
    # Cone path always carries the public-data note; empty cones add a fallback.
    res = magellan_archive.magellan_cone_search(
        "J/AJ/152/167", 225.6, -20.3, radius_arcsec=300, limit=3
    )
    assert "no public raw-frame TAP" in res["note"]
    if res["n_rows"] == 0:
        assert "fallback" in res


def test_crossmatch_external_sb2():
    ra, dec = POS_51PEG
    res = external.crossmatch_external_sb2(ra, dec, radius_arcsec=180)
    assert res["has_external_highres"] is True


def test_find_followup_targets():
    ra, dec = POS_TAU_CET
    res = external.find_followup_targets(
        ra, dec, radius_arcmin=3.0, mag_limit=12.0, max_targets=4
    )
    assert res["n_searched"] == (
        res["n_followup_candidates"] + res["n_already_covered"]
    )


def test_cone_positions_not_swapped():
    # Guard against an ra/dec swap in any cone/bbox builder. Every cone tool is
    # queried at 51 Peg (ra=344.37, dec=20.77) and the nearest returned object
    # MUST sit within the search radius of the requested position. 51 Peg is a
    # strong discriminator: swapping ra<->dec makes dec=344 (invalid, >90), so a
    # swapped CONTAINS errors and a swapped bbox returns nothing -- either way
    # this test fails loudly. n_rows>=1 alone would NOT catch a swap.
    ra, dec = POS_51PEG
    radius = 300.0

    def nearest_sep(rows, racol, deccol):
        assert rows, "no rows returned (a swap can manifest as zero rows)"
        seps = [
            _sep_arcsec(ra, dec, r[racol], r[deccol])
            for r in rows
            if r.get(racol) is not None and r.get(deccol) is not None
        ]
        assert seps, f"returned rows lack {racol}/{deccol}"
        return min(seps)

    # Gaia (cone_clause, ra/dec)
    g = gaia.gaia_cone_search(ra, dec, radius)
    assert nearest_sep(g["rows"], "ra", "dec") <= radius

    # Keck KOA (cone_clause, ra/dec)
    k = keck_koa.koa_query(instrument="HIRES", ra=ra, dec=dec, radius_arcsec=radius)
    assert nearest_sep(k["rows"], "ra", "dec") <= radius

    # ESO Phase 3 (cone_clause, s_ra/s_dec)
    p = eso.eso_phase3_query(ra=ra, dec=dec, radius_arcsec=radius)
    assert nearest_sep(p["rows"], "s_ra", "s_dec") <= radius

    # ESO raw (bbox_clause, ra/dec) -- box is a superset so allow a bit of slack.
    r_raw = eso.eso_raw_query(ra=ra, dec=dec, radius_arcsec=radius)
    assert nearest_sep(r_raw["rows"], "ra", "dec") <= radius * 1.5

    # Cross-service join
    xm = crossmatch.crossmatch(ra, dec, radius)
    assert nearest_sep(xm["gaia_dr3"]["rows"], "ra", "dec") <= radius


def test_external_three_systems_nonempty():
    # Verification (M5): >= 3 real binary / RV-monitored systems return
    # non-empty external high-resolution hits through the new crawlers.
    # (Literal El-Badry+2018b 64-system cross-check deferred: that catalog is
    # not in VizieR and the VO registry is unreachable from the build env;
    # see HANDOFF.md caveat C-M5-1.)
    systems = [
        (344.3661, 20.7689),   # 51 Peg     (Keck HIRES)
        (26.0170, -15.9374),   # tau Ceti   (ESO HARPS/ESPRESSO)
        (330.7950, 18.8843),   # HD 209458  (Keck HIRES)
        (140.6570, 50.6038),   # HD 80606   (Keck HIRES)
    ]
    n_hit = sum(
        external.crossmatch_external_sb2(ra, dec, radius_arcsec=120)[
            "has_external_highres"
        ]
        for ra, dec in systems
    )
    assert n_hit >= 3, f"only {n_hit} systems had external high-res coverage"


if __name__ == "__main__":
    for fn in (test_ges_count, test_eso_raw_4most_absent,
               test_eso_raw_giraffe_gaiaeso, test_eso_phase3_gaiaeso,
               test_eso_raw_cone_search,
               test_simbad_resolve,
               test_gaia_cone_search, test_resolve_and_enrich,
               test_ges_completeness, test_find_raw_frames,
               test_validate_against_ges, test_vizier_find_catalogs,
               test_koa_hires_cone, test_koa_schema,
               test_eso_secondary_reduced, test_eso_secondary_raw_bbox,
               test_magellan_find_catalogs, test_magellan_cone_search_note,
               test_crossmatch_external_sb2,
               test_find_followup_targets, test_cone_positions_not_swapped,
               test_external_three_systems_nonempty):
        fn()
        print(f"PASS {fn.__name__}")
    print("ALL SMOKE TESTS PASSED")
