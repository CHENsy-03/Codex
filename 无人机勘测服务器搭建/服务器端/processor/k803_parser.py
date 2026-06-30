"""5.docx §4.2 K803处理器"""
import re
class K803Processor:
    def process(self, raw: dict) -> dict:
        data = raw.get("data", {})
        raw_str = data.get("raw", "") if isinstance(data, dict) else ""
        parsed = None
        m = re.search(r"$K803,([d.]+),([d.]+),([d.]+),(d+)", str(raw))
        if m:
            parsed = {"lat": float(m.group(1)), "lng": float(m.group(2)),
                      "alt": float(m.group(3)), "quality": int(m.group(4))}
        return {"device_id": raw.get("device_id", "k803"), "status": "ok",
                "data": parsed or {"raw": str(raw)}}
