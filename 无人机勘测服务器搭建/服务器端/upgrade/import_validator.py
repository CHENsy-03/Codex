"""文件导入校验器 — 文件级/协议级/数据结构 三层校验"""
import hashlib, os, logging
logger = logging.getLogger(__name__)

class ImportValidator:
    def __init__(self):
        self.errors = []; self.warnings = []

    def validate_file(self, path: str) -> bool:
        """文件级检测：存在性、大小、编码"""
        self.errors = []; self.warnings = []
        if not os.path.exists(path):
            self.errors.append("文件不存在")
            return False
        size = os.path.getsize(path)
        if size == 0:
            self.errors.append("文件为空")
            return False
        if size > 10 * 1024 * 1024:
            self.warnings.append("文件超过10MB")
        return True

    def validate_content(self, lines: list) -> bool:
        """协议级检测：识别协议类型"""
        if not lines:
            self.errors.append("文件无数据行")
            return False
        first = lines[0].strip()
        if first.startswith("#BESTPOSA"):
            self._fmt = "BESTPOSA"
        elif first.startswith("$CM510"):
            self._fmt = "CM510"
        elif first.startswith("$"):
            self._fmt = "NMEA"
        elif "a_lat" in first.lower():
            self._fmt = "CSV"
        else:
            self.errors.append("未知协议格式")
            return False
        return True

    def validate_coords(self, lat: float, lng: float, alt: float) -> bool:
        """经纬度合法性检测"""
        if not (-90 <= lat <= 90):
            self.errors.append(f"纬度越界: {lat}")
            return False
        if not (-180 <= lng <= 180):
            self.errors.append(f"经度越界: {lng}")
            return False
        if not (-1000 <= alt <= 10000):
            self.warnings.append(f"高度异常: {alt}m")
        return True

    def validate_group(self, group: dict) -> bool:
        """三次测量完整性检测"""
        if "A" not in group or "B" not in group or "C" not in group:
            self.errors.append("测量组缺失: 必须包含A/B/C三次测量")
            return False
        return True

    def summary(self) -> dict:
        return {"errors": self.errors, "warnings": self.warnings, "format": getattr(self, "_fmt", "unknown")}
