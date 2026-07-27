# -*- coding: utf-8 -*-
"""V2.0 Region Hierarchy — 省级→市级→区县级"""
REGIONS = {
    "ZJ": {"name": "浙江", "alt_range": (0, 250),
        "cities": {
            "HZ": {"name": "杭州", "alt_range": (0, 200),
                "districts": ["上城区","下城区","江干区","拱墅区","西湖区","滨江区","萧山区","余杭区","富阳区","临安区","桐庐县","淳安县","建德市"]},
            "SX": {"name": "绍兴", "alt_range": (0, 250),
                "districts": ["越城区","柯桥区","上虞区","新昌县","诸暨市","嵊州市"]},
        }},
    "YN": {"name": "云南", "alt_range": (0, 4000),
        "cities": {
            "ZT": {"name": "昭通", "alt_range": (0, 4000),
                "districts": ["昭阳区","鲁甸县","巧家县","盐津县","大关县","永善县","绥江县","镇雄县","彝良县","威信县","水富市"]},
        }},
}
def find_region(lat, lng):
    """根据经纬度自动判断区域 (简化版)"""
    if 28.0 <= lat <= 31.5 and 118.0 <= lng <= 122.0:
        return "ZJ", "HZ" if lng < 120.5 else "SX"
    if 26.0 <= lat <= 29.0 and 102.0 <= lng <= 106.0:
        return "YN", "ZT"
    return None, None
def list_provinces():
    return [(k, v["name"]) for k, v in REGIONS.items()]
def list_cities(province_code):
    p = REGIONS.get(province_code, {})
    return [(k, v["name"]) for k, v in p.get("cities", {}).items()]
def list_districts(province_code, city_code):
    p = REGIONS.get(province_code, {})
    c = p.get("cities", {}).get(city_code, {})
    return c.get("districts", [])
def get_alt_range(province_code, city_code=None):
    p = REGIONS.get(province_code, {})
    if city_code:
        c = p.get("cities", {}).get(city_code, {})
        return c.get("alt_range", p.get("alt_range", (0, 9999)))
    return p.get("alt_range", (0, 9999))
