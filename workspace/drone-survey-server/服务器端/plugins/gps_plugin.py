"""5.docx §6.1 GPS插件"""
from upgrade.plugin_sdk import BasePlugin

class GPSPlugin(BasePlugin):
    @property
    def name(self): return "gps_plugin"
    @property
    def version(self): return "0.1.0"
    def on_event(self, data):
        payload = data.get("data", {})
        lat = float(payload.get("lat", 0))
        lng = float(payload.get("lng", 0))
        valid = 20 < lat < 40 and 100 < lng < 130
        return {"status": "success", "result": {"valid": valid, "data": payload}}
