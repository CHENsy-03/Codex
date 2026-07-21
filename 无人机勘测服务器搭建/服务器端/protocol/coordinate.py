# -*- coding: utf-8 -*-
"""V2.0 Coordinate Parsing - GPGGA DDmm.mmmm -> decimal degrees"""
import re
_DDM_RE = re.compile(r'^(\d{2,3})(\d{2}\.\d+)$')
def ddm_to_decimal(raw: str, direction: str = 'N') -> float:
    """Convert GPGGA DDmm.mmmm format to decimal degrees.
    Supports both DDmm.mmmm (latitude: 2-digit degrees) and DDDmm.mmmm (longitude: 3-digit degrees).
    """
    m = _DDM_RE.match(raw.strip())
    if not m:
        try:
            return float(raw)
        except ValueError:
            return 0.0
    degrees = int(m.group(1))
    minutes = float(m.group(2))
    decimal = degrees + minutes / 60.0
    if direction in ('S', 'W'):
        decimal = -decimal
    return round(decimal, 8)
def parse_gpgga_lat(raw_lat: str, ns: str) -> float:
    return ddm_to_decimal(raw_lat, ns)
def parse_gpgga_lng(raw_lng: str, ew: str) -> float:
    return ddm_to_decimal(raw_lng, ew)
