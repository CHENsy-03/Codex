"""序列完整性检测 — 时间和序列号跳变检测

追踪每个设备预期的序列号，检测序号跳跃/回退/时间异常。
"""
import time, logging

logger = logging.getLogger(__name__)

MAX_TIME_SKEW = 3600  # 最大允许时间偏斜（秒）
MAX_SEQ_GAP = 5       # 允许的序列号跳变上限

class SequenceChecker:
    def __init__(self):
        self._seq_state: dict[str, dict] = {}  # device_id → state

    def _get_state(self, device_id: str) -> dict:
        if device_id not in self._seq_state:
            self._seq_state[device_id] = {
                "last_seq": 0,
                "last_time": 0,
                "warnings": [],
            }
        return self._seq_state[device_id]

    def check(self, device_id: str, seq: int, survey_time: int) -> tuple[bool, str]:
        """检查序列完整性。返回 (passed, message)"""
        state = self._get_state(device_id)
        now = int(time.time())
        issues = []

        # 1. 时间异常
        if state["last_time"] > 0:
            time_diff = survey_time - state["last_time"]
            if time_diff < 0:
                issues.append(f"时间回退: {time_diff}s")
            elif time_diff > MAX_TIME_SKEW:
                issues.append(f"时间跳变: {time_diff}s (阈值{MAX_TIME_SKEW}s)")

        # 时间与当前服务器时间偏差
        time_skew = abs(now - survey_time)
        if time_skew > MAX_TIME_SKEW:
            issues.append(f"时间偏斜: {time_skew}s (设备时间与服务器时间差)")

        # 2. 序列号异常
        if state["last_seq"] > 0:
            seq_gap = seq - state["last_seq"]
            if seq_gap < 0:
                issues.append(f"序列号回退: {state['last_seq']}→{seq}")
            elif seq_gap == 0:
                issues.append(f"序列号重复: {seq}")
            elif seq_gap > MAX_SEQ_GAP:
                issues.append(f"序列号跳变: 差值{seq_gap} (上次{state['last_seq']}, 本次{seq})")

        # 3. 首条记录
        if state["last_seq"] == 0:
            issues.append(f"新设备首条记录 (seq={seq})")

        # 更新状态
        if seq > state["last_seq"]:
            state["last_seq"] = seq
        state["last_time"] = survey_time

        if issues:
            msg = "; ".join(issues)
            state["warnings"].append({"time": now, "msg": msg})
            if len(state["warnings"]) > 100:
                state["warnings"].pop(0)
            return False, msg
        return True, "序列正常"

    def stats(self, device_id: str = "") -> dict:
        if device_id:
            s = self._seq_state.get(device_id, {})
            return {"last_seq": s.get("last_seq", 0), "warnings": len(s.get("warnings", []))}
        return {
            "devices_tracked": len(self._seq_state),
            "total_warnings": sum(len(s.get("warnings", [])) for s in self._seq_state.values()),
        }

# 全局单例
_default = None
def get_default():
    global _default
    if _default is None:
        _default = SequenceChecker()
    return _default
