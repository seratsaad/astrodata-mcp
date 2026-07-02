#!/usr/bin/env python3
"""A 30-second live demo of the astrodata-mcp tools.

Runs the canonical "resolve a target, then pull nearby Gaia and Keck data"
flow directly against the real archives and prints a compact result. This is
the sequence an AI client performs when asked in natural language; running it
here makes it easy to screen-record (see docs/DEMO.md).

    python examples/demo.py            # default target: HD 122563
    python examples/demo.py "Vega"
"""
from __future__ import annotations

import sys

from astrodata_mcp.services import crossmatch, gaia, keck_koa, simbad


def main(name: str = "HD 122563") -> None:
    print(f"# Resolve {name!r} via SIMBAD")
    s = simbad.simbad_resolve(name)
    if s["n_rows"] == 0:
        print("  not found"); return
    row = s["rows"][0]
    ra, dec = row["ra"], row["dec"]
    print(f"  {row.get('main_id')}  ra={ra:.5f}  dec={dec:.5f}  type={row.get('otype_txt')}")

    print("\n# Nearest Gaia DR3 source (positions at J2016.0)")
    g = gaia.gaia_cone_search(ra, dec, radius_arcsec=10.0, limit=1)
    if g["n_rows"]:
        gr = g["rows"][0]
        print(f"  source_id={gr['source_id']}  G={gr.get('phot_g_mean_mag')}  "
              f"plx={gr.get('parallax')}  pmra={gr.get('pmra')}  pmdec={gr.get('pmdec')}")
    print(f"  epoch={g.get('epoch')}")

    print("\n# Keck HIRES frames within 1 arcmin")
    k = keck_koa.koa_query(instrument="HIRES", ra=ra, dec=dec, radius_arcsec=60.0, limit=3)
    print(f"  {k['n_rows']} frame(s)")
    for r in k["rows"][:3]:
        print(f"    {r['koaid']}  {r.get('targname')}  {r.get('date_obs')}")

    print("\n# Every result carries provenance + citation, e.g. Gaia:")
    print(f"  endpoint: {g['provenance']['endpoint']}")
    print(f"  adql:     {g['provenance']['adql'][:70]}...")
    print(f"  cite:     {g['citation'][:60]}...")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "HD 122563")
