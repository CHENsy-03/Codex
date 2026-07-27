"""K803 GNSS Module driver - UART + NMEA 0183 parsing

Standalone. Only needs: pip install pyserial

Pinout:
  K803 VCC (3.3V)  ->  Pi Pin 1
  K803 GND          ->  Pi Pin 6
  K803 TXD (output) ->  Pi Pin 10 (GPIO15 / RXD)
"""

import time

try:
    import serial as _serial_mod
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False


class K803GNSS:
    """Read GPS position from K803 module via UART"""

    def __init__(self, port="/dev/ttyAMA0", baud=9600, timeout=2):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self._ser = None

    def connect(self):
        if not HAS_SERIAL:
            raise RuntimeError("pyserial not installed: pip install pyserial")
        self._ser = _serial_mod.Serial(self.port, self.baud, timeout=self.timeout)

    def disconnect(self):
        if self._ser and self._ser.is_open:
            self._ser.close()
            self._ser = None

    def _read_line(self, timeout=5):
        """Read one NMEA sentence (blocking, up to timeout seconds)"""
        if not self._ser or not self._ser.is_open:
            self.connect()
        start = time.time()
        while time.time() - start < timeout:
            try:
                line = self._ser.readline().decode("ascii", errors="ignore").strip()
                if line.startswith("$"):
                    return line
            except Exception:
                pass
            time.sleep(0.01)
        return None

    def parse_gpgga(self, sentence):
        """Parse $GPGGA sentence -> dict with lat, lng, alt, quality"""
        if not sentence or not sentence.startswith("$GPGGA"):
            return None
        parts = sentence.split(",")
        if len(parts) < 10:
            return None
        try:
            # NMEA latitude: DDMM.MMMM -> decimal degrees
            raw_lat = parts[2]
            lat_deg = int(raw_lat[:2])
            lat_min = float(raw_lat[2:])
            lat = lat_deg + lat_min / 60.0
            if parts[3] == "S":
                lat = -lat

            # NMEA longitude: DDDMM.MMMM -> decimal degrees
            raw_lng = parts[4]
            lng_deg = int(raw_lng[:3])
            lng_min = float(raw_lng[3:])
            lng = lng_deg + lng_min / 60.0
            if parts[5] == "W":
                lng = -lng

            alt = float(parts[9]) if parts[9] else 0.0
            quality = int(parts[6]) if parts[6] else 0

            return {
                "lat": round(lat, 6),
                "lng": round(lng, 6),
                "alt": round(alt, 2),
                "quality": quality,
            }
        except (ValueError, IndexError):
            return None

    def parse_gsa(self, sentence):
        """Parse $GPGSA sentence to estimate E,N,U precision from HDOP/VDOP

        HDOP -> Horizontal error = HDOP * 150cm (UERE estimate)
        VDOP -> Vertical error   = VDOP * 150cm
        E,N   -> Horizontal split equally: E = N = HDOP_ERR / sqrt(2)
        U     -> Vertical: U = VDOP_ERR
        """
        parts = sentence.split(",")
        if len(parts) < 18:
            return None
        try:
            hdop = float(parts[16]) if parts[16] else 0.0
            vdop = float(parts[17].split("*")[0]) if parts[17] else 0.0
            if hdop <= 0:
                return None
            h_err = hdop * 150.0  # HDOP -> horizontal error in cm
            v_err = vdop * 150.0  # VDOP -> vertical error in cm
            e_n = round(h_err / 1.414, 2)  # sqrt(2)
            return {"e": e_n, "n": e_n, "u": round(v_err, 2)}
        except (ValueError, IndexError):
            return None

    def read_position(self):
        """Read one valid GPS fix. Returns None if no fix within ~30s."""
        for _ in range(60):
            line = self._read_line()
            if line and line.startswith("$GPGGA"):
                pos = self.parse_gpgga(line)
                if pos and pos["quality"] > 0:
                    return pos
        return None