"""V4-Local Plugin SDK 上下文管理"""
from dataclasses import dataclass, field

@dataclass
class PluginContext:
    plugin_name: str = ""
    plugin_version: str = "0.1.0"
    config: dict = field(default_factory=dict)
    shared_storage: dict = field(default_factory=dict)
