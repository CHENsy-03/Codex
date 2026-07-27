# -*- coding: utf-8 -*-
"""V2.1 Network Signal Monitor - multi-link scoring and auto-switch"""
import time, threading
from typing import Dict, List
from enum import Enum
class LinkType(Enum):
    LAN="lan"; N4G="4g"; N5G="5g"; WIFI="wifi"; SAT="satellite"
class SignalMonitor:
    def __init__(self):
        self._links: Dict[LinkType, dict] = {}
        self._active = LinkType.N4G
        self._lock = threading.Lock()
        for lt in LinkType:
            self._links[lt] = {"signal": 0, "latency_ms": 999, "packet_loss": 0.0,
                               "available": lt == LinkType.N4G, "score": 0.0}
    def update(self, link: LinkType, signal=0, latency_ms=999, packet_loss=0.0, available=True):
        with self._lock:
            l = self._links[link]
            l["signal"] = signal; l["latency_ms"] = latency_ms
            l["packet_loss"] = packet_loss; l["available"] = available
            l["score"] = self._calc_score(l)
    def _calc_score(self, link: dict) -> float:
        if not link["available"]:
            return 0.0
        sig = min(100, link["signal"]) / 100.0
        lat = max(0, 1.0 - min(1000, link["latency_ms"]) / 1000.0)
        loss = max(0, 1.0 - min(1.0, link["packet_loss"]))
        return sig * 0.4 + lat * 0.3 + loss * 0.3
    def best_link(self) -> LinkType:
        with self._lock:
            scored = [(lt, l["score"]) for lt, l in self._links.items() if l["available"]]
            if not scored:
                return self._active
            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[0][0]
    def switch_to(self, target: LinkType) -> bool:
        with self._lock:
            if self._links[target]["available"]:
                old = self._active
                self._active = target
                return old != target
        return False
    @property
    def active(self) -> str:
        return self._active.value
    def get_all_scores(self) -> list:
        with self._lock:
            return [{"type": lt.value, "score": round(l["score"], 3),
                     "signal": l["signal"], "latency_ms": l["latency_ms"],
                     "active": lt == self._active}
                    for lt, l in self._links.items()]
