"""精度一致性校验 — 检查报文的 sigma 与位置离散度是否匹配

如果设备报告的 E/N/U（预期精度）很小，但实际 A/B/C 之间
的位置差很大 → 精度不一致 → 标记为可疑数据。
"""
import math, logging

logger = logging.getLogger(__name__)

LAT_M = 111000.0  # 1° ≈ 111km

class PrecisionChecker:
    def __init__(self, ratio_threshold=5.0, min_dispersion=50.0):
        """ratio_threshold: 实际离散度 / 报告 sigma 的倍数阈值（默认5倍）"""
        self.ratio_threshold = ratio_threshold
        self.min_dispersion = min_dispersion  # cm - 低于此值不触发

    def check(self, A: dict, B: dict, C: dict) -> tuple[bool, str]:
        """检查精度一致性。 返回 (passed, message)"""
        # 计算实际位置离散度 (cm)
        lats = [A["lat"], B["lat"], C["lat"]]
        lngs = [A["lng"], B["lng"], C["lng"]]
        alts = [A["alt"], B["alt"], C["alt"]]

        max_lat_diff = max(lats) - min(lats)
        max_lng_diff = max(lngs) - min(lngs)
        max_alt_diff = max(alts) - min(alts)

        # 实际水平离散度 (cm)
        h_dispersion = math.sqrt(
            (max_lat_diff * LAT_M * 100) ** 2 +
            (max_lng_diff * LAT_M * 100) ** 2
        )

        # 实际垂直离散度 (cm)
        v_dispersion = max_alt_diff * 100

        # 报告的预期精度 (取最大值)
        reported_e = max(A.get("e", 0), B.get("e", 0), C.get("e", 0))
        reported_n = max(A.get("n", 0), B.get("n", 0), C.get("n", 0))
        reported_u = max(A.get("u", 0), B.get("u", 0), C.get("u", 0))

        if reported_e <= 0 or reported_n <= 0:
            return True, "sigma 数据缺失，跳过一致性校验"

        reported_h = math.sqrt(reported_e ** 2 + reported_n ** 2)

        issues = []

        # H 方向一致性
        if h_dispersion > self.min_dispersion and reported_h > 0 and h_dispersion / reported_h > self.ratio_threshold:
            issues.append(
                f"H方向: 实际离散 {h_dispersion:.1f}cm 是报告 sigma {reported_h:.1f}cm 的"
                f" {h_dispersion / reported_h:.1f}倍"
            )

        # V 方向一致性
        if v_dispersion > self.min_dispersion and reported_u > 0 and v_dispersion / reported_u > self.ratio_threshold:
            issues.append(
                f"V方向: 实际离散 {v_dispersion:.1f}cm 是报告 sigma {reported_u:.1f}cm 的"
                f" {v_dispersion / reported_u:.1f}倍"
            )

        if issues:
            msg = "精度不一致: " + "; ".join(issues)
            logger.warning(msg)
            return False, msg

        return True, "精度一致"

# 全局单例
_default = None
def get_default():
    global _default
    if _default is None:
        _default = PrecisionChecker()
    return _default
