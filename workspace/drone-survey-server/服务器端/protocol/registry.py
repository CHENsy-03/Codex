# -*- coding: utf-8 -*-
"""V2.1 Protocol Registry - pluggable parser registration"""
from typing import Dict, Optional
class ProtocolRegistry:
    def __init__(self):
        self._parsers: Dict[str, object] = {}
    def register(self, name: str, parser):
        self._parsers[name] = parser
        return self
    def get(self, name: str) -> Optional[object]:
        return self._parsers.get(name)
    def detect(self, raw: bytes) -> Optional[str]:
        for name, parser in self._parsers.items():
            if hasattr(parser, 'can_handle') and parser.can_handle(raw):
                return name
        return None
    @property
    def supported(self) -> list:
        return list(self._parsers.keys())
_global_registry = None
def get_registry():
    global _global_registry
    if _global_registry is None:
        _global_registry = ProtocolRegistry()
    return _global_registry
