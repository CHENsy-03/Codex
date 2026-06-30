"""结果服务 — 结果计算引擎

依据 4.docx §六 判定逻辑设计：
  输入: device_id
  来源: GPS对比结果 + CM510/K803插件输出 + 规则引擎
  输出: 1=正确 0=错误 -1=未知(未计算)
"""
import time, logging
from upgrade.eventbus import Event, Topics, bus
from .schema import ResultRecord
from .result_store import ResultStore

logger = logging.getLogger(__name__)

class ResultEngine:
    def __init__(self, store: ResultStore = None):
        self._store = store or ResultStore()

    def compute(self, device_id: str, data: dict = None) -> ResultRecord:
        """计算设备最终结果

        判定逻辑:
        1. 检查 GPS 定位数据有效性 (lat/lng 范围)
        2. 检查精度值 E/N/U 是否在阈值内
        3. 检查数据中是否有错误标记
        4. 综合评分
        """
        reasons = []
        score = 0
        max_score = 3

        if data is None:
            data = {}

        # 规则1: GPS 坐标范围检查
        lat = data.get("lat") or data.get("lat", 0)
        lng = data.get("lng") or data.get("lng", 0)
        if 20 < float(lat) < 40 and 100 < float(lng) < 130:
            score += 1
        else:
            reasons.append("坐标超出中国范围")

        # 规则2: 精度检查
        e = float(data.get("e", 0) or 0)
        n = float(data.get("n", 0) or 0)
        u = float(data.get("u", 0) or 0)
        max_precision = max(e, n, u)
        if max_precision < 0.1:
            score += 1
        else:
            reasons.append(f"精度超阈值: max={max_precision:.3f}m")

        # 规则3: 错误标记检查
        error = data.get("error", "") or data.get("errors", "") or ""
        if not error:
            score += 1
        else:
            reasons.append(f"含错误标记: {error}")

        # 综合判定
        if score >= max_score:
            result = 1
        elif score >= 1:
            result = 0
        else:
            result = -1

        record = ResultRecord(
            device_id=device_id,
            result=result,
            reason="; ".join(reasons) if reasons else ("全部校验通过" if result == 1 else "部分未通过"),
            source="result_engine",
        )
        self._store.save(record)
        return record

    def evaluate_batch(self, device_id: str, data_list: list[dict]) -> ResultRecord:
        """批量评估一组数据（如 A/B/C 三组）取综合结果"""
        if not data_list:
            return ResultRecord(device_id=device_id, result=-1, reason="无数据")

        results = []
        for d in data_list:
            rec = self.compute(device_id, d)
            results.append(rec.result)

        # 综合结果: 全部通过=1, 部分通过=0, 全部失败=-1
        if all(r == 1 for r in results):
            final = 1
            reason = "全部通过"
        elif all(r == -1 for r in results):
            final = -1
            reason = "全部未计算"
        else:
            final = 0
            reason = f"部分未通过: {results}"

        record = ResultRecord(device_id=device_id, result=final, reason=reason, source="batch")
        self._store.save(record)
        return record
