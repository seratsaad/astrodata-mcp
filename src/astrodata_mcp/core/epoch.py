"""Proper-motion / epoch propagation.

Positions in different catalogues are valid at different epochs: Gaia DR3 is
J2016.0, most legacy catalogues are J2000.0, and observation-time positions vary.
For a high-proper-motion star those positions differ by arcseconds -- enough to
miss a cross-match or match a neighbour. This propagates a position from one
epoch to another using its proper motion (and distance / RV when available).
"""
from __future__ import annotations

import warnings

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time

# Common reference epochs (Julian years).
GAIA_DR3 = 2016.0
J2000 = 2000.0


def propagate(
    ra: float,
    dec: float,
    pmra: float,
    pmdec: float,
    from_epoch: float,
    to_epoch: float,
    parallax: float | None = None,
    radial_velocity: float | None = None,
) -> dict:
    """Propagate a sky position by proper motion between two epochs.

    Angles in degrees; `pmra` is pm_ra*cos(dec) and `pmdec` in mas/yr (the Gaia
    convention); epochs in Julian years (e.g. 2016.0). Optional `parallax` (mas)
    and `radial_velocity` (km/s) give a fuller 3D treatment; without them the
    tangential proper motion is applied. Returns the new ra/dec and the total
    angular shift in arcsec.
    """
    kw = dict(
        ra=ra * u.deg,
        dec=dec * u.deg,
        pm_ra_cosdec=pmra * u.mas / u.yr,
        pm_dec=pmdec * u.mas / u.yr,
        obstime=Time(from_epoch, format="jyear"),
    )
    if parallax is not None and parallax > 0:
        kw["distance"] = (1000.0 / parallax) * u.pc
    if radial_velocity is not None:
        kw["radial_velocity"] = radial_velocity * u.km / u.s
    start = SkyCoord(**kw)
    with warnings.catch_warnings():
        # ERFA notes a harmless "distance overridden" when propagating without
        # a full 3D solution; the sky position is still correct.
        warnings.simplefilter("ignore")
        moved = start.apply_space_motion(new_obstime=Time(to_epoch, format="jyear"))
    return {
        "ra": float(moved.ra.deg),
        "dec": float(moved.dec.deg),
        "from_epoch": from_epoch,
        "to_epoch": to_epoch,
        "shift_arcsec": round(float(start.separation(moved).arcsec), 4),
    }
