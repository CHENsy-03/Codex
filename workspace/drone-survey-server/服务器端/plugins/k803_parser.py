"""K803 GNSS 模块报文解析插件

解析 K803 EK0407 板卡输出的自定义定位报文。
"""
import re, logging
from upgrade.plugin_sdk import BasePlugin

logger = logging.getLogger(__name__)

class K803ParserPlugin(BasePlugin):
    @property
    def name(self): return "k803_parser"
    @property
    def version(self): return "0.1.0"

    def on_event(self, data):
        payload = data.get("data", {})
        raw = payload.get("raw", "")
        if not raw:
            return {"status": "fail", "result": {}, "error": "no raw data"}
        parsed = self._parse(raw)
        if parsed:
            return {"status": "success", "result": {"parsed": parsed}}
        return {"status": "success", "result": {"parsed": None}}

    def _parse(self, raw):
        # K803 典型报文: $K803,lat,lng,alt,quality*XX
        m = re.match(r"^$K803,([d.]+),([d.]+),([d.]+),(d+)", raw)
        if m:
            return {"lat": float(m.group(1)), "lng": float(m.group(2)),
                    "alt": float(m.group(3)), "quality": int(m.group(4)),
                    "format": "K803"}
        return None
