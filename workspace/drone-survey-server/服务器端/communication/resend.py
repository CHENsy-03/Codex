# -*- coding: utf-8 -*-
"""V2.0 Resend - 超时重传引擎

策略：
1. 指数退避: 1s -> 2s -> 4s -> 8s -> 16s (max)
2. 最大重试 3 次，超出后标记为失败
3. 失败消息自动转入离线队列
4. 后台线程定期扫描待重传消息
"""

import time
import threading
from typing import Optional, Callable, Dict
from dataclasses import dataclass, field


@dataclass
class ResendRecord:
    """单条重传记录"""
    msg_id: int = 0
    device_id: str = ""
    sequence: int = 0
    payload: bytes = b""
    send_time: float = 0.0
    retry_count: int = 0
    max_retries: int = 3
    next_retry_at: float = 0.0
    status: str = "pending"       # pending / retrying / failed / acked


@dataclass
class ResendStats:
    """重传统计"""
    total_sent: int = 0
    total_acked: int = 0
    total_retried: int = 0
    total_failed: int = 0
    pending_count: int = 0


class ResendManager:
    """重传管理器"""

    # 退避策略：重试次数 -> 等待秒数
    BACKOFF_SCHEDULE = {0: 1.0, 1: 2.0, 2: 4.0, 3: 8.0}

    def __init__(self, max_retries: int = 3, scan_interval: float = 1.0):
        self.max_retries = max_retries
        self.scan_interval = scan_interval

        # 待确认消息
        self._pending: Dict[str, ResendRecord] = {}  # key = f"{device_id}:{sequence}"
        self._lock = threading.Lock()

        # 后台线程
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # 回调
        self._send_callback: Optional[Callable] = None   # (device_id, payload) -> bool
        self._fail_callback: Optional[Callable] = None   # (device_id, sequence, payload) -> None (转入离线队列)

        # DB 引用
        self._db: Optional[object] = None

        # 统计
        self.stats = ResendStats()

    # ── 依赖注入 ──

    def set_db(self, db):
        self._db = db

    def set_send_callback(self, callback: Callable):
        """设置发送回调: (device_id, payload) -> bool"""
        self._send_callback = callback

    def set_fail_callback(self, callback: Callable):
        """设置失败回调: (device_id, sequence, payload) -> None"""
        self._fail_callback = callback

    # ── 生命周期 ──

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._scan_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    # ── 注册待确认消息 ──

    def register(self, device_id: str, sequence: int, payload: bytes):
        """发送消息后注册，等待 ACK"""
        key = f"{device_id}:{sequence}"
        now = time.time()
        with self._lock:
            self._pending[key] = ResendRecord(
                msg_id=0,
                device_id=device_id,
                sequence=sequence,
                payload=payload,
                send_time=now,
                retry_count=0,
                max_retries=self.max_retries,
                next_retry_at=now + self.BACKOFF_SCHEDULE.get(0, 1.0),
                status="pending",
            )
        self.stats.total_sent += 1
        self.stats.pending_count = len(self._pending)

    # ── ACK/NACK 处理 ──

    def on_ack(self, device_id: str, sequence: int):
        """收到 ACK，移除重传记录"""
        key = f"{device_id}:{sequence}"
        with self._lock:
            if key in self._pending:
                del self._pending[key]
                self.stats.total_acked += 1
        self.stats.pending_count = len(self._pending)

    def on_nack(self, device_id: str, sequence: int):
        """收到 NACK，立即触发重传"""
        key = f"{device_id}:{sequence}"
        with self._lock:
            if key in self._pending:
                rec = self._pending[key]
                rec.next_retry_at = time.time()  # 立即重试

    # ── 后台扫描 ──

    def _scan_loop(self):
        """后台线程：定期扫描超时消息并重传"""
        while self._running:
            try:
                self._scan_and_retry()
            except Exception:
                pass
            time.sleep(self.scan_interval)

    def _scan_and_retry(self):
        now = time.time()
        to_retry = []
        to_fail = []

        with self._lock:
            for key, rec in list(self._pending.items()):
                if rec.status == "acked":
                    continue
                if rec.retry_count >= rec.max_retries:
                    to_fail.append(key)
                elif now >= rec.next_retry_at:
                    to_retry.append(key)

            for key in to_fail:
                rec = self._pending.pop(key, None)
                if rec:
                    rec.status = "failed"
                    self.stats.total_failed += 1
                    # 转入离线队列
                    if self._fail_callback:
                        try:
                            self._fail_callback(rec.device_id, rec.sequence, rec.payload)
                        except Exception:
                            pass
                    # 同时写入 DB 离线表
                    if self._db:
                        try:
                            self._db.enqueue_offline(rec.device_id, rec.sequence, rec.payload)
                        except Exception:
                            pass

        # 执行重传 (在锁外进行，避免回调死锁)
        for key in to_retry:
            with self._lock:
                rec = self._pending.get(key)
                if rec is None:
                    continue
            self._do_retry(rec)

        self.stats.pending_count = len(self._pending)

    def _do_retry(self, rec: ResendRecord):
        """执行单次重传"""
        with self._lock:
            rec.retry_count += 1
            backoff = self.BACKOFF_SCHEDULE.get(rec.retry_count, 8.0)
            rec.next_retry_at = time.time() + backoff
            rec.status = "retrying"

        self.stats.total_retried += 1

        if self._send_callback:
            try:
                self._send_callback(rec.device_id, rec.payload)
            except Exception:
                pass

    # ── 手动重传 ──

    def retry_all_pending(self) -> int:
        """手动触发所有待确认消息的重传"""
        count = 0
        with self._lock:
            for rec in list(self._pending.values()):
                if rec.status in ("pending", "retrying"):
                    rec.next_retry_at = time.time()
                    count += 1
        return count

    def reset_device(self, device_id: str):
        """清除指定设备的所有待确认消息"""
        with self._lock:
            keys_to_remove = [k for k in self._pending if k.startswith(f"{device_id}:")]
            for k in keys_to_remove:
                del self._pending[k]
        self.stats.pending_count = len(self._pending)

    # ── 统计 ──

    def get_statistics(self) -> dict:
        return {
            "total_sent": self.stats.total_sent,
            "total_acked": self.stats.total_acked,
            "total_retried": self.stats.total_retried,
            "total_failed": self.stats.total_failed,
            "pending_count": self.stats.pending_count,
            "is_running": self._running,
        }

    def get_pending_list(self) -> list:
        with self._lock:
            return [
                {
                    "device_id": r.device_id,
                    "sequence": r.sequence,
                    "retry_count": r.retry_count,
                    "status": r.status,
                    "next_retry_sec": max(0, r.next_retry_at - time.time()),
                }
                for r in list(self._pending.values())
            ]
