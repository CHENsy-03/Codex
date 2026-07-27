"""勘测引擎 — 3次测量 → 扩展检查 → 上传"""
import time, threading, logging
from extensions import ExtensionManager, RTKQualityCheck, SetupStabilityCheck
from transporter import create_transporter
from gps_reader import create_reader

logger = logging.getLogger(__name__)

class SurveyEngine:
    """一次完整勘测任务的生命周期管理"""

    def __init__(self, config, reader=None, transporter=None):
        self.cfg = config
        self.reader = reader
        self.transporter = transporter
        self.ext_mgr = ExtensionManager()
        self._running = False
        self._seq = 0
        self._setup_extensions()

    def _setup_extensions(self):
        if getattr(self.cfg, "enable_rtk_quality", True):
            self.ext_mgr.register(RTKQualityCheck())
        if getattr(self.cfg, "enable_stability", False):
            self.ext_mgr.register(SetupStabilityCheck())
        # IMU / 双天线为预留状态，默认不注册
        # if getattr(self.cfg, "enable_imu_check", False):
        #     self.ext_mgr.register(IMUOrientationCheck())

    def read_one_fix(self, label="") -> dict | None:
        """读取一次有效的 GNSS 定位"""
        if not self.reader:
            logger.error("No GNSS reader")
            return None
        fix = self.reader.read_fix()
        if fix:
            fix["label"] = label
            fix["seq"] = self._seq
            self.ext_mgr.record_all(fix)
            logger.info("  %s fix: lat=%.6f lng=%.6f alt=%.1f src=%s",
                        label, fix["lat"], fix["lng"], fix["alt"], fix.get("source","?"))
            return fix
        return None

    def run_survey(self) -> tuple[bool, dict, list[str]]:
        """执行一次完整勘测: A → B → C → 扩展检查 → 上传"""
        self._seq += 1
        seq = self._seq
        log = []
        log.append(f"Survey #{seq}")

        # 1. 三次测量
        samples = []
        for label in ("A", "B", "C"):
            fix = self.read_one_fix(label)
            if not fix:
                log.append(f"  {label}: 定位失败")
                continue
            fix.setdefault("e", 0.5); fix.setdefault("n", 0.6); fix.setdefault("u", 1.5)
            samples.append(fix)
            time.sleep(1)  # 测量间隔

        if len(samples) < 3:
            log.append("  FAIL: 未获取到 3 次有效定位")
            return False, {}, log

        # 2. 扩展检测
        for fix in samples:
            all_ok, ext_msgs = self.ext_mgr.run_all(fix)
            log.extend(ext_msgs)
            if not all_ok:
                log.append(f"  FAIL: {fix['label']} 扩展检测未通过")
                return False, {"A": samples[0], "B": samples[1], "C": samples[2]}, log

        # 3. 上传
        payload = {
            "device_id": self.cfg.device_id,
            "seq": seq,
            "survey_time": int(time.time()),
            "A": samples[0], "B": samples[1], "C": samples[2],
        }
        if self.transporter:
            ok = self.transporter.send(payload)
            log.append(f"  上传: {'成功' if ok else '失败'}")
            if not ok:
                return False, payload, log
        else:
            log.append("  无传输通道 (dry run)")
            return True, payload, log

        # 4. 等待响应
        if self.transporter:
            resp = self.transporter.receive(timeout=5)
            if resp:
                status = resp.get("status", "")
                log.append(f"  响应: {status} - {resp.get('message','')}")
                return status == "success", payload, log

        return True, payload, log
