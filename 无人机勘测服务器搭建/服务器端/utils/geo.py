
"""Geographic utilities: polygon containment, region routing"""


class BBox:
    """Bounding box for fast pre-filter"""
    def __init__(self, min_lat, max_lat, min_lng, max_lng):
        self.min_lat = min_lat
        self.max_lat = max_lat
        self.min_lng = min_lng
        self.max_lng = max_lng

    def contains(self, lat, lng):
        return self.min_lat <= lat <= self.max_lat and self.min_lng <= lng <= self.max_lng


def point_in_polygon(lat, lng, polygon):
    """Ray-casting algorithm: check if point is inside polygon.

    polygon: list of (lat, lng) tuples forming a closed polygon.
    Returns True/False.
    """
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        yi, xi = polygon[i]
        yj, xj = polygon[j]
        # Does horizontal ray from point intersect edge (i,j)?
        if ((yi > lat) != (yj > lat)) and            (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def which_polygon(lat, lng, regions):
    """Return region_code of the polygon containing (lat, lng), or None."""
    for region_code, cfg in regions.items():
        boundary = cfg.get("boundary")
        if not boundary:
            continue
        # Fast bbox check first
        bbox = boundary.get("_bbox")
        if bbox and not bbox.contains(lat, lng):
            continue
        # Precise polygon check
        if point_in_polygon(lat, lng, boundary["points"]):
            return region_code
    return None


def build_bbox(points):
    """Build bounding box from polygon points"""
    lats = [p[0] for p in points]
    lngs = [p[1] for p in points]
    return BBox(min(lats), max(lats), min(lngs), max(lngs))
