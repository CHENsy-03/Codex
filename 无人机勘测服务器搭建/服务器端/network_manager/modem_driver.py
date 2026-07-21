# -*- coding: utf-8 -*-
"""V2.1 4G Modem Driver - AT command interface for Quectel/Huawei/ZTE"""
import serial, time, threading, re
from typing import Optional, Dict
class ModemDriver:
    def __init__(self, port="COM3", baudrate=115200, timeout=3):
        self.port = port; self.baudrate = baudrate; self.timeout = timeout
        self._ser = None; self._lock = threading.Lock()
    def open(self) -> bool:
        try:
            self._ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            return True
        except Exception:
            return False
    def close(self):
        if self._ser:
            try: self._ser.close()
            except Exception: pass
            self._ser = None
    def _at_command(self, cmd: str, wait_ms=500) -> str:
        with self._lock:
            if not self._ser or not self._ser.is_open:
                return ""
            self._ser.write((cmd + "\r\n").encode())
            time.sleep(wait_ms / 1000.0)
            result = ""
            while self._ser.in_waiting:
                result += self._ser.read(self._ser.in_waiting).decode(errors="ignore")
            return result
    def get_signal(self) -> int:
        resp = self._at_command("AT+CSQ")
        m = re.search(r"\+CSQ:\s*(\d+)", resp)
        return int(m.group(1)) * 100 // 31 if m else 0
    def get_operator(self) -> str:
        resp = self._at_command("AT+COPS?")
        m = re.search(r"\+COPS:\s*\d+,\d+,\"([^\"]+)\"", resp)
        return m.group(1) if m else "unknown"
    def get_ip(self) -> str:
        resp = self._at_command("AT+CGPADDR=1")
        m = re.search(r"\+CGPADDR:\s*\d+,([\d.]+)", resp)
        return m.group(1) if m else ""
    def restart(self) -> bool:
        self._at_command("AT+CFUN=0", 2000)
        self._at_command("AT+CFUN=1", 3000)
        return self.get_signal() > 0
    def is_connected(self) -> bool:
        resp = self._at_command("AT+CGATT?")
        return "+CGATT: 1" in resp
    def get_status(self) -> dict:
        return {"signal": self.get_signal(), "operator": self.get_operator(),
                "ip": self.get_ip(), "connected": self.is_connected()}
