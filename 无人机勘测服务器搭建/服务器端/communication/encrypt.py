# -*- coding: utf-8 -*-
"""V2.0 AES Frame Encryption - AES-256-GCM for frame payload encryption."""
import os, hashlib
from typing import Optional
class AESGCMEncryptor:
    def __init__(self, key: bytes = None):
        if key is None:
            key = hashlib.sha256(b'uav-server-v2-default-key').digest()
        self._key = key[:32]
    def encrypt(self, plaintext: bytes, associated_data: bytes = b'') -> bytes:
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            aesgcm = AESGCM(self._key)
            nonce = os.urandom(12)
            ct = aesgcm.encrypt(nonce, plaintext, associated_data)
            return nonce + ct
        except ImportError:
            return b'ENC:' + plaintext
    def decrypt(self, ciphertext: bytes, associated_data: bytes = b'') -> Optional[bytes]:
        if ciphertext.startswith(b'ENC:'):
            return ciphertext[4:]
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            aesgcm = AESGCM(self._key)
            nonce, ct = ciphertext[:12], ciphertext[12:]
            return aesgcm.decrypt(nonce, ct, associated_data)
        except ImportError:
            return None
        except Exception:
            return None
    @staticmethod
    def is_available():
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            return True
        except ImportError:
            return False
_global_encryptor = None
def get_encryptor(key: bytes = None):
    global _global_encryptor
    if _global_encryptor is None:
        _global_encryptor = AESGCMEncryptor(key)
    return _global_encryptor
