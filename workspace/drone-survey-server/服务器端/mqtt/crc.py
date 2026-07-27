
"""Data integrity: CRC32 checksum + sequence tracking per message

Each MQTT message carries:
  - crc: CRC32 of all other fields (detect corruption)
  - seq: monotonic sequence number (detect gaps/drops)
"""

import zlib
import json
import logging

logger = logging.getLogger(__name__)


def compute_crc(data: dict) -> int:
    """Compute CRC32 of a dict (sort keys for deterministic result)"""
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return zlib.crc32(payload.encode()) & 0xFFFFFFFF


def verify_message(msg: dict) -> bool:
    """Verify the CRC32 field in a message matches the content

    The msg dict must contain a 'crc' key with the expected CRC value.
    Returns True if CRC matches or no CRC field (backward compat).
    """
    expected = msg.get("crc")
    if expected is None:
        return True  # no CRC = skip check (backward compat)
    # Recompute without the crc field
    check_data = dict(msg)
    check_data.pop("crc", None)
    actual = compute_crc(check_data)
    if actual != expected:
        logger.warning("CRC mismatch: expected=%s actual=%s", expected, actual)
        return False
    return True


def add_crc(msg: dict) -> dict:
    """Add CRC32 field to a message before sending"""
    msg["crc"] = compute_crc(msg)
    return msg


class SequenceTracker:
    """Track sequence numbers to detect message gaps

    Usage:
        tracker = SequenceTracker()
        gaps = tracker.check(seq=7)  # returns [(5,6)] if seq 5,6 were missed
    """
    def __init__(self, initial_seq=0):
        self._last_seq = initial_seq

    def check(self, seq: int) -> list:
        """Return list of (from, to) tuple ranges that were missed"""
        if seq <= self._last_seq:
            return []  # duplicate or out-of-order, ignore
        gaps = []
        if seq > self._last_seq + 1:
            gaps.append((self._last_seq + 1, seq - 1))
        self._last_seq = seq
        return gaps

    @property
    def last_seq(self) -> int:
        return self._last_seq
