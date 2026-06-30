"""Parser plugin base class

All parsers must inherit ParserPlugin and implement:
  - can_handle(raw) -> bool
  - parse(raw) -> dict | None
"""

class ParserPlugin:
    """Base class for format parsers (NMEA, BESTPOS, etc.)"""

    @staticmethod
    def can_handle(raw) -> bool:
        """Return True if this parser can handle the given raw data"""
        raise NotImplementedError

    @staticmethod
    def parse(raw) -> dict or None:
        """Parse raw data into standard format.

        Returns dict with keys:
          - position: {"lat": float, "lng": float, "alt": float,
                        "h": float, "v": float, "d": float}
          - device_id: str (optional, auto-detect or blank)
          - survey_time: int (optional, unix timestamp)
          - quality: int (optional, 0-1 for validity)
        Returns None if parsing fails.
        """
        raise NotImplementedError


def auto_detect(raw) -> list:
    """Try all registered plugins in order. Returns [(name, result), ...]"""
    results = []
    # Late imports to avoid circular deps
    from .nmea import NMEAParser
    from .bestpos import BESTPOSParser, BESTPOSASCIIParser

    for name, parser in [("nmea", NMEAParser), ("bestpos", BESTPOSParser), ("bestposa", BESTPOSASCIIParser)]:
        try:
            if parser.can_handle(raw):
                result = parser.parse(raw)
                if result:
                    results.append((name, result))
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Parser %s error: %s", name, e)
    return results
