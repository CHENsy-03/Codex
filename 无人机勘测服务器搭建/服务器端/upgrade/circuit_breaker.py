"""熔断机制 — 某勘测员错误率超过阈值时临时隔离

维护滑动窗口（最多 N 条记录），计算最近通过率。
错误率 > threshold 时触发熔断，设备被隔离。
隔离持续 cooldown 秒后自动重置，或手动恢复。
"""
import time, logging

logger = logging.getLogger(__name__)

class CircuitBreaker:
    def __init__(self, window_size=100, error_threshold=0.3, cooldown=300):
        self.window_size = window_size       # 滑动窗口大小
        self.error_threshold = error_threshold  # 触发熔断的错误率
        self.cooldown = cooldown             # 隔离冷却时间(秒)
        self._history: dict[str, list[bool]] = {}  # device_id → [passed, ...]
        self._isolated: dict[str, float] = {}      # device_id → isolation_time

    def record(self, device_id: str, passed: bool):
        """记录一次勘测结果"""
        if device_id not in self._history:
            self._history[device_id] = []
        self._history[device_id].append(passed)
        if len(self._history[device_id]) > self.window_size:
            self._history[device_id].pop(0)

        # 计算错误率
        err_rate = self._error_rate(device_id)
        if err_rate > self.error_threshold and device_id not in self._isolated:
            self._isolated[device_id] = time.time()
            logger.warning(
                "CIRCUIT BREAKER: %s isolated (error rate %.1f%% > %.0f%%)",
                device_id, err_rate * 100, self.error_threshold * 100
            )

    def check(self, device_id: str) -> tuple[bool, str]:
        now = time.time()
        # Check throttled state
        if device_id in self._isolated:
            elapsed = now - self._isolated[device_id]
            if elapsed > self.cooldown:
                del self._isolated[device_id]
                return True, "熔断已恢复"
            remaining = self.cooldown - elapsed
            return (False, 
                    f"设备已隔离(错误率{self._error_rate(device_id)*100:.0f}%)"
                    f" 剩余{remaining:.0f}s")
        
        # Auto-throttle: if recent error rate > 50%, return throttle signal
        err_rate = self._error_rate(device_id)
        if err_rate > self.error_threshold and self._history.get(device_id, []):
            return (True, 
                    f"请求已接收，但该设备错误率{err_rate*100:.0f}%偏高，建议暂停")
        
        return True, "正常"
        """检查设备是否被熔断。返回 (allowed, message)"""
        now = time.time()

        # 检查是否已过冷却期 → 自动恢复
        if device_id in self._isolated:
            elapsed = now - self._isolated[device_id]
            if elapsed > self.cooldown:
                del self._isolated[device_id]
                logger.info("Circuit breaker reset: %s (cooldown %ds elapsed)", device_id, self.cooldown)
                return True, "熔断已恢复"

            remaining = self.cooldown - elapsed
            return False, (
                f"设备已被隔离(错误率{self._error_rate(device_id)*100:.0f}% > {self.error_threshold*100:.0f}%)"
                f" 剩余{remaining:.0f}s"
            )

        return True, "正常"

    def _error_rate(self, device_id: str) -> float:
        h = self._history.get(device_id, [])
        if not h:
            return 0.0
        return sum(1 for p in h if not p) / len(h)

    def reset(self, device_id: str = ""):
        """手动恢复设备"""
        if device_id:
            self._isolated.pop(device_id, None)
            self._history.pop(device_id, None)
        else:
            self._isolated.clear()
            self._history.clear()

    def throttle_remaining(self, device_id: str) -> float:
        """返回设备剩余冷却时间(秒)，0=未隔离"""
        if device_id in self._isolated:
            elapsed = time.time() - self._isolated[device_id]
            return max(0, self.cooldown - elapsed)
        return 0.0

    def stats(self) -> dict:
        result = {}
        for device_id in set(list(self._history.keys()) + list(self._isolated.keys())):
            rate = self._error_rate(device_id)
            result[device_id] = {
                "samples": len(self._history.get(device_id, [])),
                "error_rate": round(rate, 3),
                "isolated": device_id in self._isolated,
                "remaining_cooldown": round(
                    max(0, self.cooldown - (time.time() - self._isolated[device_id]))
                ) if device_id in self._isolated else 0,
            }
        return result

# 全局单例
_default = None
def get_default():
    global _default
    if _default is None:
        _default = CircuitBreaker()
    return _default
