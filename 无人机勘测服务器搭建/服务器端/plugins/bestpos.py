"""BESTPOS (NovAtel binary) parser plugin

Handles: NovAtel OEM7 binary log format
Output: standard position dict with stddev-based accuracy

Binary header sync: 0xAA 0x44 0x12 0x1C
Message ID for BESTPOS: 42 (0x002A)
"""

import struct
import time
from .base import ParserPlugin


class BESTPOSParser(ParserPlugin):
    """Parse NovAtel BESTPOS binary logs"""

    SYNC = b"\xAA\x44\x12\x1C"
    MSG_ID_BESTPOS = 42

    # Position type enum
    POS_TYPE = {
        0: "NONE",
        32: "SINGLE",
        16: "RTXDGPS",
        4: "RTKFLOAT",
        5: "RTKFIXED",
    }

    @staticmethod
    def can_handle(raw) -> bool:
        if isinstance(raw, str):
            return False
        if not isinstance(raw, (bytes, bytearray)):
            return False
        return len(raw) >= 80 and raw[:4] == BESTPOSParser.SYNC

    @staticmethod
    def parse(raw: bytes) -> dict or None:
        """Parse BESTPOS binary message -> position dict

        Expects at least 84 bytes:
          - 28 byte header
          - ~52 byte body (varies by version)
          - 4 byte CRC
        """
        if not BESTPOSParser.can_handle(raw):
            return None

        try:
            # Header (28 bytes)
            # struct format: <HHHHIIBBxI (sync already checked)
            hdr = struct.unpack("<HHHHIIBBxI", raw[4:32])
            msg_id = hdr[0]
            msg_len = hdr[4]

            if msg_id != BESTPOSParser.MSG_ID_BESTPOS:
                return None

            # Body - common version (offset 28).
            # Fields: solstat(4B), postype(4B), lat(4B), lng(4B),
            #         hgt(8B), undulation(8B), vel(4B), heading(4B),
            #         num_tracked(2B), num_used(2B),
            #         hdop(4B), vdop(4B), pdop(4B),
            #         lat_std(8B), lng_std(8B), hgt_std(8B)
            body = raw[28:84]

            # Unpack body
            (solstat, postype, lat, lng,
             hgt, undulation,
             vel, heading,
             num_tracked, num_used,
             hdop, vdop, pdop,
             lat_std, lng_std, hgt_std) = struct.unpack("<IIffddffHHffffdddd", body[:72])

            # Check solution validity
            quality = 1 if solstat == 4 else 0  # SOLSTAT = 4 means valid

            # Standard deviations are in meters. Convert to cm.
            h_cm = round(lat_std * 100, 2) if lat_std > 0 else 150.0
            v_cm = round(lng_std * 100, 2) if lng_std > 0 else 200.0
            d_cm = round(hgt_std * 100, 2) if hgt_std > 0 else 250.0

        except: return None


# --- enhanced full-field parser ---
def parse_bestposa_full(raw):
    parts=raw.split(chr(44))
    if len(parts)<24:return None
    try:
        sol_stat=parts[9].split(chr(59))[1] if chr(59) in parts[9] else chr(63)
        pos_type=parts[10] if len(parts)>10 else chr(63)
        lat=float(parts[11]);lng=float(parts[12]);hgt=float(parts[13])
        undulation=float(parts[14])/100 if parts[14] else 0
        datum=parts[15] if len(parts)>15 else chr(63)
        lat_sigma=float(parts[16]) if parts[16] else 0
        lon_sigma=float(parts[17]) if parts[17] else 0
        hgt_sigma=float(parts[18]) if parts[18] else 0
        diff_age=float(parts[20]) if len(parts)>20 and parts[20] else 0
        sol_age=float(parts[21]) if len(parts)>21 and parts[21] else 0
        sv_tracked=int(parts[22]) if len(parts)>22 and parts[22] else 0
        sv_used=int(parts[23]) if len(parts)>23 and parts[23] else 0
        return dict(sol_stat=sol_stat,pos_type=pos_type,lat=lat,lng=lng,hgt=hgt,
            undulation=undulation,datum=datum,lat_sigma=lat_sigma,lon_sigma=lon_sigma,
            hgt_sigma=hgt_sigma,diff_age=diff_age,sol_age=sol_age,
            sv_tracked=sv_tracked,sv_in_solution=sv_used,source=chr(66)+chr(69)+chr(83)+chr(84)+chr(80)+chr(79)+chr(83))
    except:return None


class BESTPOSASCIIParser(ParserPlugin):
    """Parse NovAtel BESTPOS ASCII logs (#BESTPOSA format)"""

    @staticmethod
    def can_handle(raw) -> bool:
        if isinstance(raw, bytes):
            try:
                raw = raw.decode("utf-8", errors="ignore")
            except Exception:
                return False
        return raw.strip().startswith("#BESTPOSA")

    @staticmethod
    def parse(raw) -> dict or None:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="ignore")
        raw = raw.strip()
        if not raw.startswith("#BESTPOSA"):
            return None
        parts = raw.split(",")
        if len(parts) < 24:
            return None
        try:
            lat = float(parts[11])
            lng = float(parts[12])
            alt = float(parts[13])
            std_lat = float(parts[16]) if parts[16] else 0.005
            std_lng = float(parts[17]) if parts[17] else 0.006
            std_hgt = float(parts[18]) if parts[18] else 0.015
            e_cm = round(std_lat * 100, 2)
            n_cm = round(std_lng * 100, 2)
            u_cm = round(std_hgt * 100, 2)
            pos_type = parts[10] if len(parts) > 10 else "UNKNOWN"
            quality = 1
            if pos_type == "NARROW_INT":
                quality = 1
            elif pos_type == "NARROW_FLOAT":
                quality = 2
            elif pos_type == "SINGLE":
                quality = 3
                e_cm = max(e_cm, 50.0)
                n_cm = max(n_cm, 50.0)
                u_cm = max(u_cm, 100.0)
            return {
                "lat": round(lat, 6), "lng": round(lng, 6),
                "alt": round(alt, 2), "e": e_cm, "n": n_cm, "u": u_cm,
                "quality": quality, "pos_type": pos_type,
                "num_sats": int(parts[23]) if parts[23] else 0,
                "source": "BESTPOSA",
            }
        except (ValueError, IndexError):
            return None


        except: return None


# --- enhanced full-field parser ---
