"""Canonical data-acknowledgement strings for each archive.

Astronomers must cite the archives and catalogues their data came from. Every
result returned by this server carries the required acknowledgement so it can be
pasted straight into a paper. These are the standard wordings published by each
data centre; keep them verbatim.
"""
from __future__ import annotations

CITATIONS: dict[str, str] = {
    "ESO": (
        "Based on data obtained from the ESO Science Archive Facility."
    ),
    "Gaia": (
        "This work has made use of data from the European Space Agency (ESA) "
        "mission Gaia (https://www.cosmos.esa.int/gaia), processed by the Gaia "
        "Data Processing and Analysis Consortium (DPAC, "
        "https://www.cosmos.esa.int/web/gaia/dpac/consortium). Funding for the "
        "DPAC has been provided by national institutions, in particular the "
        "institutions participating in the Gaia Multilateral Agreement."
    ),
    "SIMBAD": (
        "This research has made use of the SIMBAD database, operated at CDS, "
        "Strasbourg, France (2000, A&AS, 143, 9, Wenger et al.)."
    ),
    "VizieR": (
        "This research has made use of the VizieR catalogue access tool, CDS, "
        "Strasbourg, France (DOI: 10.26093/cds/vizier). The original "
        "description of the VizieR service was published in 2000, A&AS 143, 23."
    ),
    "KOA": (
        "This research has made use of the Keck Observatory Archive (KOA), "
        "which is operated by the W. M. Keck Observatory and the NASA Exoplanet "
        "Science Institute (NExScI), under contract with the National "
        "Aeronautics and Space Administration."
    ),
}


def citation_for(source: str | None) -> str | None:
    """Return the acknowledgement string for a source key, or None."""
    if source is None:
        return None
    return CITATIONS.get(source)


def vizier_cite_path(catalog: str) -> str:
    """A pointer to the source paper / bibcode for a specific VizieR catalogue.

    VizieR catalogues each wrap a published paper; the bibcode and full
    reference are on the catalogue's VizieR page. Cite that paper in addition to
    the VizieR tool acknowledgement.
    """
    return (
        f"Cite the source paper for catalogue '{catalog}'. Its bibcode and "
        f"reference are at https://vizier.cds.unistra.fr/viz-bin/VizieR?-source={catalog}"
    )
