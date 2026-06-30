"""5.docx §3.5 Stream Pipeline"""
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)

class StreamPipeline:
    def __init__(self):
        self._stages = []

    def add_stage(self, name: str, handler: Callable) -> "StreamPipeline":
        self._stages.append((name, handler))
        return self

    def process(self, event: dict) -> Optional[dict]:
        current = event
        for name, handler in self._stages:
            try:
                current = handler(current)
                if current is None:
                    return None
            except Exception as e:
                logger.error("Pipeline stage %s error: %s", name, e)
                return None
        return current
