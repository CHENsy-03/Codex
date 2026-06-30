
"""Gateway entry point — simulates the API Gateway layer.

In production, this would be a FastAPI/Flask service behind Nginx/Kong.
This module ties together: verification chain, region routing,
idempotency, and the shard database.
"""

import logging
from auth.verifier import (
    default_verify_chain, VerifyContext, VerifyResult,
    DeviceCertVerifier, SourceHashVerifier, TimestampNonceVerifier,
    SignatureVerifier, JWTVerifier, FaceRecognitionVerifier,
    VerifyChain,
)
from utils.geo import which_polygon
from utils.admin_regions import find_admin
from utils.device_store import get_device
from cache.idempotency import IdempotencyManager
from shard_db import ShardDatabase
from db_config import REGION_CONFIG
from upgrade.duplicate_detector import get_default as get_dup_detector
from upgrade.sequence_checker import get_default as get_seq_checker
from upgrade.circuit_breaker import get_default as get_cb

logger = logging.getLogger(__name__)


class SurveyGateway:
    """Gateway for processing survey data from devices.

    Handles: verification -> region routing -> processing -> idempotency
    """

    def __init__(self, verify_chain=None):
        self.verify_chain = verify_chain or default_verify_chain()
        self.idempotency = IdempotencyManager()
        self.dup_detector = get_dup_detector()
        self.seq_checker = get_seq_checker()
        self.circuit_breaker = get_cb()

    def resolve_region(self, device_id, lat=None, lng=None):
        """Three-layer region resolution:
        1. Device registration (pre-configured)
        2. GPS coordinates (polygon containment)
        3. Fallback
        """
        # Layer 1: device registration
        dev = get_device(device_id)
        device_region = dev["region_code"] if dev else None

        # Layer 2: GPS coordinates
        gps_region = None
        if lat is not None and lng is not None:
            _ad = find_admin(lat, lng)
            _cm = {'\u676d\u5dde': 'hangzhou', '\u7ecd\u5174': 'shaoxing', '\u662d\u901a\u5e02': 'zhaotong'}
            gps_region = _cm.get(_ad.get('l1', '')) or which_polygon(lat, lng, REGION_CONFIG)

        # Layer 3: reconcile
        if device_region and gps_region and device_region != gps_region:
            logger.warning(
                "Cross-region: device=%s claims %s, GPS says %s",
                device_id, device_region, gps_region
            )
            # Default: trust GPS (device may be roaming)
            return gps_region

        return device_region or gps_region or "hangzhou"

    def process_survey(self, device_id, A, B, C, batch_id=None,
                       lat=None, lng=None, verify_ctx=None,
                       survey_time=None):
        """Process a single survey data submission.

        Returns (success: bool, message: str, result_dict: dict)
        """
        # 1. Verification
        if verify_ctx:
            result = self.verify_chain.verify(verify_ctx)
            if not result.passed:
                return False, result.message, {"status": "auth_fail"}

        # 2. Idempotency check
        bid = batch_id or f"{device_id}-{int(__import__('time').time())}"
        if self.idempotency.already_processed(device_id, bid):
            cached = self.idempotency.get_result(device_id, bid)
            if cached and cached.get("status") == "success":
                return True, "Already processed (idempotent)", cached
            return False, "Previously failed, retry allowed", {}

        # 3. Region routing
        avg_lat = (A["lat"] + B["lat"] + C["lat"]) / 3.0
        avg_lng = (A["lng"] + B["lng"] + C["lng"]) / 3.0
        region = self.resolve_region(device_id, avg_lat, avg_lng)

        if not region:
            return False, "Unrecognized survey region", {}

        # 4. Process via ShardDatabase
        try:
            with ShardDatabase(region) as shard:
                ok, msg = shard.insert_survey_data(A, B, C, survey_time=survey_time)

            result = {
                "status": "success" if ok else "failed",
                "message": msg,
                "region": region,
                "batch_id": bid,
            }

            self.idempotency.store_result(device_id, bid, result)
            return ok, msg, result

        except Exception as e:
            logger.error("Survey processing error: %s", e, exc_info=True)
            self.idempotency.mark_failed(device_id, bid)
            return False, str(e), {"status": "error"}
