"""
模拟GPS定位脚本 - TCP发送模块
将GPS报文以ASCII文本形式通过TCP发送（每行一条报文）
"""

import asyncio
import logging

log = logging.getLogger('GPS.Sender')


class TcpSender:
    """GPS报文TCP发送器 - 直接发送ASCII报文文本."""

    def __init__(self, host='localhost', port=9001):
        self.host = host
        self.port = port
        self.writer = None
        self.reader = None
        self.sent = 0
        self.failed = 0

    async def start(self):
        """建立到目标的TCP连接."""
        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), timeout=5
            )
            log.info(f"已连接 {self.host}:{self.port}")
        except Exception as e:
            log.warning(f"TCP连接失败: {e}")
            raise

    async def send(self, msg: str):
        """发送一条报文（追加换行符后发送）."""
        if not self.writer:
            raise ConnectionError("未建立TCP连接")
        try:
            data = (msg + '\n').encode('ascii')
            self.writer.write(data)
            await self.writer.drain()
            self.sent += 1
            return len(data)
        except Exception as e:
            self.failed += 1
            raise

    async def close(self):
        """关闭TCP连接."""
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass
        log.info(f"TCP发送器已关闭. 成功: {self.sent}, 失败: {self.failed}")

