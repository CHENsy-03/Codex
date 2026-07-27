"""NMEA 0183 parser plugin

Handles: $GPGGA, $GPGSA, $GPRMC, $GPGSV
Output: standard position dict

Usage:
    from plugins.nmea import NMEAParser
    if NMEAParser.can_handle(raw):
        result = NMEAParser.parse(raw)
"""

import time
from .base import ParserPlugin


class NMEAParser(ParserPlugin):
    """Parse NMEA 0183 sentences into standard position format"""

    # Buffer: device_id -> [fix_dict, ...] accumulate 3 fixes for A/B/C
    _buffer = {}

    @staticmethod
    def can_handle(raw) -> bool:
        if isinstance(raw, bytes):
            try:
                raw = raw.decode("ascii", errors="ignore")
            except Exception:
                return False
        return raw.startswith("$GP") or raw.startswith("$GN")

    @staticmethod
    def parse_gga(sentence: str) -> dict or None:
        """Parse $GPGGA sentence -> position dict"""
        parts = sentence.split(",")
        if len(parts) < 10 or not parts[2] or not parts[4]:
            return None
        try:
            if parts[6] in ("", "0"):
                return None  # no fix

            # Latitude: DDMM.MMMM
            raw_lat = parts[2]
            lat = int(raw_lat[:2]) + float(raw_lat[2:]) / 60.0
            if parts[3] == "S":
                lat = -lat

            # Longitude: DDDMM.MMMM
            raw_lng = parts[4]
            lng = int(raw_lng[:3]) + float(raw_lng[3:]) / 60.0
            if parts[5] == "W":
                lng = -lng

            alt = float(parts[9]) if parts[9] else 0.0
            quality = int(parts[6]) if parts[6] else 0
            num_sats = int(parts[7]) if parts[7] else 0
            hdop_val = float(parts[8]) if parts[8] else 0.0

            return {
                "lat": round(lat, 6),
                "lng": round(lng, 6),
                "alt": round(alt, 2),
                "quality": quality,
                "num_sats": num_sats,
                "hdop": hdop_val,
                "source": "GGA",
            }
        except (ValueError, IndexError):
            return None

    @staticmethod
    def parse_gsa(sentence: str) -> dict or None:
        """Parse $GPGSA sentence -> DOP values"""
        parts = sentence.split(",")
        if len(parts) < 18:
            return None
        try:
            pdop = float(parts[15]) if parts[15] else 0.0
            hdop = float(parts[16]) if parts[16] else 0.0
            vdop = float(parts[17].split("*")[0]) if parts[17] else 0.0
            return {"hdop": hdop, "vdop": vdop, "pdop": pdop, "source": "GSA"}
        except (ValueError, IndexError):
            return None

    @staticmethod
    def dop_to_cm(dop: float, base_accuracy_cm: float = 150.0) -> float:
        """Convert DOP to approximate cm accuracy

        HDOP/VDOP are unitless multipliers.
        Common formula: accuracy = DOP * UERE (user equivalent range error)
        For consumer GPS, typical UERE = 1.5m -> 150cm
        """
        return round(dop * base_accuracy_cm, 2)

    @classmethod
    def parse(cls, raw) -> dict or None:
        """Parse one NMEA sentence. Returns position dict or None."""
        if isinstance(raw, bytes):
            raw = raw.decode("ascii", errors="ignore")

        raw = raw.strip()
        if not raw:
            return None

        # Route to specific parser based on sentence type
        sentence_type = raw[3:6] if len(raw) > 6 else ""

        if sentence_type == "GGA":
            return cls.parse_gga(raw)
        elif sentence_type == "GSA":
            return cls.parse_gsa(raw)
        elif sentence_type == "RMC":
            # RMC has timestamp but no position in a usable format for us
            # Just skip - we only use GGA for position
            return None
        elif sentence_type in ("GSV", "GLL", "VTG"):
            return None  # supplementary data, not primary position

        return None

    @classmethod
    def parse_position_with_dop(cls, gga_raw: str, gsa_raw: str = None) -> dict or None:
        """Parse GGA + optional GSA into complete position with accuracy estimates"""
        pos = cls.parse_gga(gga_raw)
        if not pos:
            return None

        # Try to get DOP values for H/V/D estimation
        if gsa_raw:
            dop = cls.parse_gsa(gsa_raw)
            if dop:
                pos["h"] = cls.dop_to_cm(dop["hdop"])
                pos["v"] = cls.dop_to_cm(dop["vdop"])
                pos["d"] = cls.dop_to_cm(dop["pdop"])
        else:
            # Default accuracy values if no DOP available
            pos["h"] = 150.0
            pos["v"] = 200.0
            pos["d"] = 250.0

        return pos
