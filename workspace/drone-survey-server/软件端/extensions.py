"""硬件扩展点 — 为未来 IMU/双天线/稳定性检测预留接口"""
import abc, time, math, logging

logger = logging.getLogger(__name__)

class HardwareExtension(abc.ABC):
    @property
    @abc.abstractmethod
    def name(self) -> str:
        """扩展名称"""
        ...

    @abc.abstractmethod
    def check(self, fix: dict) -> tuple[bool, str]:
        """执行检测. 返回 (通过, 消息)"""
        ...

    def on_enable(self):
        pass

    def on_disable(self):
        pass


class RTKQualityCheck(HardwareExtension):
    """[已实现] RTK固定解检测 — 只接受 NARROW_INT / FIXED 解算类型"""
    ALLOWED_TYPES = {"NARROW_INT", "RTK_FIXED", "FIXED", "RTK_FIX"}

    @property
    def name(self):
        return "RTK Quality"

    def check(self, fix: dict) -> tuple[bool, str]:
        pos_type = fix.get("pos_type", fix.get("source", "UNKNOWN"))
        quality = fix.get("quality", 0)
        if pos_type in self.ALLOWED_TYPES:
            return True, f"RTK fixed OK ({pos_type})"
        if quality >= 4:  # RTK fix in NMEA quality
            return True, f"RTK fixed OK (quality={quality})"
        return False, f"Not RTK fixed ({pos_type}, quality={quality})"


class IMUOrientationCheck(HardwareExtension):
    """
    [预留] IMU姿态检测
    
    未来实现:
    - 读取加速度计/陀螺仪
    - 检测设备是否水平、稳定
    - 检测测量过程中杆/三脚架是否移动
    """
    @property
    def name(self):
        return "IMU Orientation"

    def check(self, fix: dict) -> tuple[bool, str]:
        # TODO: 接入 IMU 传感器 (MPU6050 / ICM-20948)
        return True, "IMU: N/A (not implemented)"


class DualAntennaBaselineCheck(HardwareExtension):
    """
    [预留] 双天线基线校验
    
    未来实现:
    - 读取两个 GNSS 天线的位置
    - 计算基线长度（已知物理间距）
    - 若解算长度 ≠ 实际长度 → 架站偏移
    """
    @property
    def name(self):
        return "Dual Antenna Baseline"

    def check(self, fix: dict) -> tuple[bool, str]:
        # TODO: 实现双天线基线验证
        return True, "Dual antenna: N/A (not implemented)"


class SetupStabilityCheck(HardwareExtension):
    """
    [预留] 架站稳定性检测
    
    未来实现:
    - 测量前监测 5-10 秒位置
    - 计算位置方差
    - 若方差超限 → 拒绝（架站不稳）
    """
    @property
    def name(self):
        return "Setup Stability"

    def __init__(self, window=10):
        self._history = []
        self._window = window

    def check(self, fix: dict) -> tuple[bool, str]:
        # TODO: 实现稳定性监测
        return True, "Stability: N/A (not implemented)"

    def record(self, fix: dict):
        """记录一次位置用于稳定性分析"""
        self._history.append((fix.get("lat", 0), fix.get("lng", 0), fix.get("alt", 0)))
        if len(self._history) > self._window:
            self._history.pop(0)


class ExtensionManager:
    """扩展管理器 — 注册 + 执行"""

    def __init__(self):
        self._extensions: list[HardwareExtension] = []

    def register(self, ext: HardwareExtension):
        self._extensions.append(ext)
        logger.info("Extension registered: %s", ext.name)

    def run_all(self, fix: dict) -> tuple[bool, list[str]]:
        all_ok = True
        msgs = []
        for ext in self._extensions:
            try:
                ok, msg = ext.check(fix)
                if not ok:
                    all_ok = False
                msgs.append(f"[{ext.name}] {msg}")
                logger.debug("Extension %s: %s", ext.name, msg)
            except NotImplementedError:
                msgs.append(f"[{ext.name}] skipped")
            except Exception as e:
                logger.warning("Extension %s error: %s", ext.name, e)
        return all_ok, msgs

    def record_all(self, fix: dict):
        """传递 fix 给需要记录历史的扩展"""
        for ext in self._extensions:
            if hasattr(ext, "record"):
                ext.record(fix)
