
"""MQTT + device configuration (env vars > config dict > defaults)

All secrets/configurations come from environment variables in production.
For development, you can pass a dict or use a config.yaml file.

Priority: env var > config dict > default value
"""

import os
import logging

logger = logging.getLogger(__name__)


def env_or(key, default=""):
    """Get from env var (case-insensitive), fallback to default"""
    return os.environ.get(key, os.environ.get(key.upper(), default))


class MQTTConfig:
    """MQTT connection configuration"""

    def __init__(self, **overrides):
        self._overrides = overrides

    @property
    def broker_host(self) -> str:
        return self._overrides.get("broker_host") or env_or("MQTT_HOST", "localhost")

    @property
    def broker_port(self) -> int:
        return int(self._overrides.get("broker_port") or env_or("MQTT_PORT", "8883"))

    @property
    def use_tls(self) -> bool:
        val = self._overrides.get("use_tls") or env_or("MQTT_TLS", "true")
        return str(val).lower() in ("true", "1", "yes")

    @property
    def ca_path(self) -> str:
        return self._overrides.get("ca_path") or env_or("MQTT_CA", "")

    @property
    def cert_path(self) -> str:
        return self._overrides.get("cert_path") or env_or("MQTT_CERT", "")

    @property
    def key_path(self) -> str:
        return self._overrides.get("key_path") or env_or("MQTT_KEY", "")

    @property
    def username(self) -> str:
        return self._overrides.get("username") or env_or("MQTT_USER", "")

    @property
    def password(self) -> str:
        return self._overrides.get("password") or env_or("MQTT_PASS", "")

    @property
    def client_id(self) -> str:
        return self._overrides.get("client_id") or env_or("DEVICE_ID", "survey-device")

    @property
    def keepalive(self) -> int:
        return int(self._overrides.get("keepalive") or env_or("MQTT_KEEPALIVE", "60"))


class DeviceConfig:
    """Device survey configuration"""

    def __init__(self, **overrides):
        self._overrides = overrides

    @property
    def device_id(self) -> str:
        return self._overrides.get("device_id") or env_or("DEVICE_ID", "DEV-001")

    @property
    def hmac_key(self) -> str:
        return self._overrides.get("hmac_key") or env_or("HMAC_KEY", "")

    @property
    def survey_interval(self) -> int:
        return int(self._overrides.get("survey_interval") or env_or("SURVEY_INTERVAL", "60"))

    @property
    def gps_port(self) -> str:
        return self._overrides.get("gps_port") or env_or("GPS_PORT", "/dev/ttyAMA0")

    @property
    def gps_baud(self) -> int:
        return int(self._overrides.get("gps_baud") or env_or("GPS_BAUD", "9600"))
