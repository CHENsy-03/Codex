"""5.docx §4.2 Rule Engine"""
import time, logging
logger = logging.getLogger(__name__)

class RuleEngine:
    def evaluate(self, device_id: str, data: dict) -> dict:
        issues = []
        lat = float(data.get("lat", 0))
        lng = float(data.get("lng", 0))
        if not (20 < lat < 40): issues.append(f"lat={lat}")
        if not (100 < lng < 130): issues.append(f"lng={lng}")
        e, n, u = float(data.get("e", 0)), float(data.get("n", 0)), float(data.get("u", 0))
        if max(e, n, u) > 0.1: issues.append("precision")
        valid = len(issues) == 0
        return {"device_id": device_id, "valid": valid, "issues": issues, "result": 1 if valid else 0}
