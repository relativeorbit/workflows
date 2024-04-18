#!/usr/bin/env python
"""
get a list of bursts intersecting a WKT geometry
"""

import asf_search as asf
import sys

WKT = sys.argv[1]
ABSORB = sys.argv[2]
POL = sys.argv[3]

results = asf.geo_search(
    platform=[asf.PLATFORM.SENTINEL1],
    processingLevel=asf.PRODUCT_TYPE.BURST,
    polarization=POL,
    intersectsWith=WKT,
    absoluteOrbit=int(ABSORB),
)
" ".join([r.properties["fileID"] for r in results])
print(" ".join([r.properties["fileID"] for r in results]))