"""Plugin SDK Base — 插件标准基类

符合 V4-Local Step4 规范。
重导出 upgrade/plugin_sdk 的 BasePlugin。
"""
from upgrade.plugin_sdk import BasePlugin, PluginContext, PluginInput, PluginOutput
__all__ = ["BasePlugin", "PluginContext", "PluginInput", "PluginOutput"]
