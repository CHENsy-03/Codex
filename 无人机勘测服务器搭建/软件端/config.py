"""Board configuration — edit .env or set environment variables"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def env(key, default=""):
    return os.environ.get(key, os.environ.get(key.upper(), default))

class Config:
    # ── Device ──
    @property
    def device_id(self): return env("DEVICE_ID", "K803-001")

    # ── GNSS Reader (K803_EK0407) ──
    @property
    def gps_mode(self): return env("GPS_MODE", "serial")     # "serial" | "tcp" | "udp"
    @property
    def gps_port(self): return env("GPS_PORT", "/dev/ttyAMA0")
    @property
    def gps_baud(self): return int(env("GPS_BAUD", "115200"))
    @property
    def gps_timeout(self): return float(env("GPS_TIMEOUT", "3.0"))

    # ── Transport (CM510-71F) ──
    @property
    def transport(self): return env("TRANSPORT", "mqtt")      # "mqtt" | "tcp" | "udp"
    @property
    def cm510_host(self): return env("CM510_HOST", "192.168.1.100")
    @property
    def cm510_port(self): return int(env("CM510_PORT", "8888"))
    @property
    def cm510_timeout(self): return float(env("CM510_TIMEOUT", "5.0"))

    # ── MQTT (fallback) ──
    @property
    def mqtt_host(self): return env("MQTT_HOST", "localhost")
    @property
    def mqtt_port(self): return int(env("MQTT_PORT", "1883"))
    @property
    def mqtt_user(self): return env("MQTT_USER", "")
    @property
    def mqtt_pass(self): return env("MQTT_PASS", "")
    @property
    def mqtt_topic_survey(self): return env("MQTT_TOPIC_SURVEY", "survey/data")
    @property
    def mqtt_topic_response(self): return env("MQTT_TOPIC_RESPONSE", "survey/response")

    # ── Survey ──
    @property
    def survey_interval(self): return int(env("SURVEY_INTERVAL", "10"))

    # ── Security ──
    @property
    def hmac_key(self): return env("HMAC_KEY", "")

    # ── Extension toggles (预留扩展开关) ──
    @property
    def enable_rtk_quality(self): return env("ENABLE_RTK_QUALITY", "true").lower() == "true"
    @property
    def enable_imu_check(self): return env("ENABLE_IMU_CHECK", "false").lower() == "true"
    @property
    def enable_dual_antenna(self): return env("ENABLE_DUAL_ANTENNA", "false").lower() == "true"
    @property
    def enable_stability(self): return env("ENABLE_STABILITY", "false").lower() == "true"

cfg = Config()
