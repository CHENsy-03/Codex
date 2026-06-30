
"""Pluggable verification chain for device/auth validation.

Each step is a Verifier subclass. Add new steps via chain.add() without
modifying existing code. See FaceRecognitionVerifier for example.
"""

import hashlib
import hmac
import json
import time
from typing import NamedTuple


class VerifyResult(NamedTuple):
    passed: bool
    message: str


class VerifyContext:
    """Context passed through the verification chain.

    Each verifier can read and write to this context.
    """
    def __init__(self, device_id="", source_hash="", token="",
                 cert_fingerprint="", face_vector=None,
                 timestamp=0, nonce="", signature="", secret_key=""):
        self.device_id = device_id
        self.source_hash = source_hash
        self.token = token
        self.cert_fingerprint = cert_fingerprint
        self.face_vector = face_vector
        self.timestamp = timestamp
        self.nonce = nonce
        self.signature = signature
        self.secret_key = secret_key
        self.extra = {}  # custom data


class Verifier:
    """Base class for all verifiers"""
    def check(self, ctx: VerifyContext) -> VerifyResult:
        raise NotImplementedError


class VerifyChain:
    """Pluggable verification chain.

    Usage:
        chain = VerifyChain()
        chain.add(Step1Verifier())
        chain.add(Step2Verifier())
        result = chain.verify(ctx)
    """
    def __init__(self):
        self._steps = []

    def add(self, verifier: Verifier):
        self._steps.append(verifier)
        return self

    def verify(self, ctx: VerifyContext) -> VerifyResult:
        for step in self._steps:
            result = step.check(ctx)
            if not result.passed:
                return result
        return VerifyResult(True, "All verifications passed")


# ── Concrete Verifiers ──────────────────────────

class DeviceCertVerifier(Verifier):
    """Verify device certificate fingerprint"""
    def __init__(self):
        from utils.device_store import check_cert
        self._check_cert = check_cert

    def check(self, ctx: VerifyContext) -> VerifyResult:
        if not ctx.device_id:
            return VerifyResult(False, "Missing device_id")
        if not self._check_cert(ctx.device_id, ctx.cert_fingerprint):
            return VerifyResult(False, "Device certificate mismatch")
        return VerifyResult(True, "Device cert verified")


class SourceHashVerifier(Verifier):
    """Verify mini-program source code hash"""
    ALLOWED_HASHES = [
        "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",  # known good versions
    ]

    def check(self, ctx: VerifyContext) -> VerifyResult:
        if not ctx.source_hash:
            return VerifyResult(False, "Missing source hash")
        if ctx.source_hash not in self.ALLOWED_HASHES:
            return VerifyResult(False, "Source code hash not authorized")
        return VerifyResult(True, "Source hash verified")


class TimestampNonceVerifier(Verifier):
    """Anti-replay: timestamp must be within 5 min, nonce unused"""
    MAX_AGE = 300  # 5 minutes
    _used_nonces = set()  # in production: Redis SET with TTL

    def check(self, ctx: VerifyContext) -> VerifyResult:
        now = time.time()
        if abs(now - ctx.timestamp) > self.MAX_AGE:
            return VerifyResult(False, "Timestamp out of range")
        if ctx.nonce in self._used_nonces:
            return VerifyResult(False, "Nonce already used (replay)")
        self._used_nonces.add(ctx.nonce)
        return VerifyResult(True, "Timestamp + nonce OK")


class SignatureVerifier(Verifier):
    """HMAC-SHA256 signature verification"""
    def check(self, ctx: VerifyContext) -> VerifyResult:
        if not ctx.secret_key:
            return VerifyResult(True, "No secret key configured, skipping")
        if not ctx.signature:
            return VerifyResult(False, "Missing signature")
        payload = f"{ctx.device_id}|{ctx.timestamp}|{ctx.nonce}|{ctx.source_hash}"
        expected = hmac.new(
            ctx.secret_key.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, ctx.signature):
            return VerifyResult(False, "Signature mismatch")
        return VerifyResult(True, "Signature verified")


class FaceRecognitionVerifier(Verifier):
    """Face recognition verifier — pluggable, can be added/removed freely.

    In production, replace cosine_similarity with your model inference.
    Face vectors are 128-dim float arrays from a face embedding model.
    """
    def __init__(self, threshold=0.85):
        self.threshold = threshold
        from utils.device_store import get_face_embedding
        self._get_embedding = get_face_embedding
        self._model_loaded = False

    def _load_model(self):
        """Lazy load face model — replace with your actual model"""
        self._model_loaded = True

    def _cosine_similarity(self, v1, v2):
        """Cosine similarity between two vectors"""
        if not v1 or not v2:
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        n1 = sum(a * a for a in v1) ** 0.5
        n2 = sum(b * b for b in v2) ** 0.5
        if n1 == 0 or n2 == 0:
            return 0.0
        return dot / (n1 * n2)

    def check(self, ctx: VerifyContext) -> VerifyResult:
        if ctx.face_vector is None:
            return VerifyResult(True, "No face data, skipping")
        if not self._model_loaded:
            self._load_model()

        stored = self._get_embedding(ctx.device_id)
        if stored is None:
            return VerifyResult(False, "No face registered for device")

        similarity = self._cosine_similarity(ctx.face_vector, stored)
        if similarity >= self.threshold:
            return VerifyResult(True, f"Face match: {similarity:.3f}")
        return VerifyResult(
            False, f"Face mismatch: {similarity:.3f} < {self.threshold}"
        )


class JWTVerifier(Verifier):
    """Simple JWT-like token verification (no external lib needed)

    Token format: base64(device_id|expiry|signature)
    In production, use PyJWT library with RS256.
    """
    def __init__(self, secret="default-secret-change-in-prod"):
        self.secret = secret
        import base64
        self._b64 = base64

    def _sign(self, payload):
        import hashlib
        return hashlib.sha256((payload + self.secret).encode()).hexdigest()[:16]

    def issue_token(self, device_id, expiry=1800):
        """Issue a temporary token (30 min validity)"""
        payload = f"{device_id}|{int(time.time()) + expiry}"
        sig = self._sign(payload)
        token = self._b64.b64encode(f"{payload}|{sig}".encode()).decode()
        return token

    def check(self, ctx: VerifyContext) -> VerifyResult:
        if not ctx.token:
            return VerifyResult(False, "Missing token")
        try:
            decoded = self._b64.b64decode(ctx.token.encode()).decode()
            parts = decoded.split("|")
            if len(parts) != 3:
                return VerifyResult(False, "Invalid token format")
            device_id, expiry_str, sig = parts
            sig_check = self._sign(f"{device_id}|{expiry_str}")
            if sig != sig_check:
                return VerifyResult(False, "Token signature invalid")
            if int(time.time()) > int(expiry_str):
                return VerifyResult(False, "Token expired")
            return VerifyResult(True, "JWT verified")
        except Exception:
            return VerifyResult(False, "Token parse error")


# ── Factory: build a standard chain ─────────────

def default_verify_chain(include_face=False):
    """Build the default verification chain.

    Add face recognition by passing include_face=True.
    No existing code changes needed when adding new verifiers.
    """
    chain = VerifyChain()
    chain.add(DeviceCertVerifier())
    chain.add(SourceHashVerifier())
    chain.add(TimestampNonceVerifier())
    chain.add(SignatureVerifier())
    chain.add(JWTVerifier())
    if include_face:
        chain.add(FaceRecognitionVerifier())
    return chain
