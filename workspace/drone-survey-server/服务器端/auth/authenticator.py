# -*- coding: utf-8 -*-
"""V2.0 Device Authenticator - device token verification."""
import time, hashlib, hmac, threading
class DeviceAuthenticator:
    def __init__(self, secret_key: str = 'uav-server-v2-secret'):
        self._secret = secret_key.encode('utf-8')
        self._authorized = set()
        self._lock = threading.Lock()
    def register_device(self, device_id: str, device_secret: str = ''):
        token = hmac.new(self._secret, device_id.encode(), hashlib.sha256).hexdigest()[:16]
        with self._lock:
            self._authorized.add(device_id)
        return token
    def verify(self, device_id: str, token: str) -> bool:
        expected = hmac.new(self._secret, device_id.encode(), hashlib.sha256).hexdigest()[:16]
        if not hmac.compare_digest(token, expected):
            return False
        with self._lock:
            self._authorized.add(device_id)
        return True
    def is_authorized(self, device_id: str) -> bool:
        with self._lock:
            return device_id in self._authorized
    def revoke(self, device_id: str):
        with self._lock:
            self._authorized.discard(device_id)
    @property
    def stats(self):
        with self._lock:
            return {'authorized_devices': len(self._authorized),
                    'devices': sorted(self._authorized)}
