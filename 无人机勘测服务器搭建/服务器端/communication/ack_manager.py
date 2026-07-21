"""ACK Manager V2.0 - ACK/NACK 确认 + 重传队列"""

import time
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Callable


@dataclass
class PendingMessage:
    """待确认消息"""
    device_id: str
    sequence: int
    payload: bytes
    send_time: int = field(default_factory=lambda: int(time.time() * 1000))
    retry_count: int = 0
    status: str = "pending"          # pending / acked / failed


class AckManager:
    """ACK/NACK 消息确认 + 重传管理"""

    def __init__(self, max_retries: int = 3,
                 base_timeout_ms: int = 1000,
                 max_timeout_ms: int = 16000,
                 window_size: int = 32):
        self.max_retries = max_retries
        self.base_timeout_ms = base_timeout_ms
        self.max_timeout_ms = max_timeout_ms
        self.window_size = window_size

        self._pending: Dict[str, Dict[int, PendingMessage]] = {}
        self._lock = threading.Lock()
        self._send_callback: Optional[Callable] = None
        self._db = None

        # 统计
        self.stats = {"sent": 0, "acked": 0, "nacked": 0, "retransmitted": 0, "failed": 0}

    def set_db(self, db):
        self._db = db

    def set_send_callback(self, callback: Callable):
        """设置重传回调函数 callback(device_id, payload)"""
        self._send_callback = callback

    def register_send(self, device_id: str, sequence: int, payload: bytes):
        """注册一条已发送消息 (等待ACK)"""
        with self._lock:
            msg = PendingMessage(device_id=device_id, sequence=sequence, payload=payload)
            if device_id not in self._pending:
                self._pending[device_id] = {}
            self._pending[device_id][sequence] = msg
            self.stats["sent"] += 1

    def process_ack(self, device_id: str, ack_sequence: int) -> bool:
        """处理收到的ACK"""
        with self._lock:
            dev_pending = self._pending.get(device_id, {})
            msg = dev_pending.get(ack_sequence)
            if msg:
                msg.status = "acked"
                self.stats["acked"] += 1
                # 清理已确认的旧消息
                self._cleanup_device(device_id, ack_sequence)
                return True
            return False

    def process_nack(self, device_id: str, nack_sequence: int) -> bool:
        """处理收到的NACK"""
        with self._lock:
            dev_pending = self._pending.get(device_id, {})
            msg = dev_pending.get(nack_sequence)
            if msg:
                msg.retry_count = self.max_retries  # 标记为需要重传
                self.stats["nacked"] += 1
                return True
            return False

    def get_retransmit_list(self) -> List[PendingMessage]:
        """获取需要重传的消息列表 (调用方负责实际发送)"""
        now = int(time.time() * 1000)
        retry_list = []
        with self._lock:
            for device_id, dev_pending in self._pending.items():
                for seq, msg in list(dev_pending.items()):
                    # 检查是否超时
                    if msg.status == "pending":
                        elapsed = now - msg.send_time
                        timeout = min(self.base_timeout_ms * (2 ** msg.retry_count),
                                      self.max_timeout_ms)
                        if elapsed > timeout:
                            if msg.retry_count < self.max_retries:
                                msg.retry_count += 1
                                msg.send_time = now
                                retry_list.append(msg)
                                self.stats["retransmitted"] += 1
                            else:
                                msg.status = "failed"
                                self.stats["failed"] += 1
        return retry_list

    def _cleanup_device(self, device_id: str, acked_seq: int):
        """清理已确认序列之前的消息"""
        dev_pending = self._pending.get(device_id, {})
        old_seqs = [s for s in dev_pending if s <= acked_seq and dev_pending[s].status == "acked"]
        for s in old_seqs:
            del dev_pending[s]

    def get_statistics(self) -> dict:
        with self._lock:
            pending_count = sum(len(m) for m in self._pending.values())
            return {**self.stats, "pending": pending_count}

    def reset(self):
        self.stop_scan()
        with self._lock:
            self._pending.clear()
            self.stats = {"sent": 0, "acked": 0, "nacked": 0, "retransmitted": 0, "failed": 0}

    def restore_pending_from_db(self, device_id: str = None) -> int:
        """服务器重启后从数据库恢复待确认消息到内存"""
        if not self._db:
            return 0
        records = self._db.load_ack_pending(device_id)
        count = 0
        with self._lock:
            for r in records:
                dev_id = r["device_id"]; seq = r["sequence"]
                if dev_id not in self._pending:
                    self._pending[dev_id] = {}
                if seq not in self._pending[dev_id]:
                    msg = PendingMessage(device_id=dev_id, sequence=seq,
                                         payload=r.get("payload", b""))
                    self._pending[dev_id][seq] = msg
                    count += 1
        return count
    def start_scan(self, interval=5.0):
        if hasattr(self, '_scan_thread') and self._scan_thread and self._scan_thread.is_alive():
            return
        self._scan_running = True
        self._scan_thread = threading.Thread(target=self._scan_loop, args=(interval,), daemon=True)
        self._scan_thread.start()
    def stop_scan(self):
        self._scan_running = False
    def _scan_loop(self, interval):
        while getattr(self, '_scan_running', False):
            retry_list = self.get_retransmit_list()
            for msg in retry_list:
                if self._send_callback:
                    try: self._send_callback(msg.device_id, msg.payload)
                    except Exception: pass
            time.sleep(interval)
