"""5.docx §3.3 标准Topic定义"""
class Topic:
    DEVICE_RAW = "device.raw"
    DEVICE_PARSED = "device.parsed"
    GPS_DATA = "gps.data"
    SIGNAL_CM510 = "signal.cm510"
    SIGNAL_K803 = "signal.k803"
    ANALYSIS_RESULT = "analysis.result"
    SYSTEM_ANOMALY = "system.anomaly"

    @classmethod
    def list(cls):
        return [v for k, v in vars(cls).items() if not k.startswith("_") and isinstance(v, str)]
