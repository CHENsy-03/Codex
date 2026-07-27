"""V4 Plugin SDK — 标准化插件系统，支持沙箱超时执行"""
import abc, threading, time, logging, traceback

logger = logging.getLogger(__name__)

class BasePlugin(abc.ABC):
    @property
    @abc.abstractmethod
    def name(self) -> str:
        """插件名称"""

    @abc.abstractmethod
    def on_data(self, data: dict):
        """处理一条数据"""

    def on_start(self):
        """插件启动时调用"""

    def on_stop(self):
        """插件停止时调用"""

    def on_error(self, data: dict, error: Exception):
        """处理异常"""


class PluginManager:
    def __init__(self, sandbox_timeout=10):
        self._plugins = {}
        self._timeout = sandbox_timeout

    def register(self, plugin: BasePlugin):
        if plugin.name in self._plugins:
            logger.warning("Plugin %s already registered, replacing", plugin.name)
        self._plugins[plugin.name] = plugin
        plugin.on_start()
        logger.info("Plugin registered: %s", plugin.name)

    def unregister(self, name: str):
        if name in self._plugins:
            self._plugins[name].on_stop()
            del self._plugins[name]

    def process(self, data: dict) -> dict:
        """用沙箱执行所有插件"""
        results = {}
        for name, plugin in self._plugins.items():
            result = {"status": "ok", "output": None}
            try:
                output = []
                def run():
                    try:
                        plugin.on_data(data)
                    except Exception as e:
                        output.append(e)
                t = threading.Thread(target=run, daemon=True)
                t.start()
                t.join(timeout=self._timeout)
                if t.is_alive():
                    result["status"] = "timeout"
                elif output:
                    raise output[0]
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)
                try:
                    plugin.on_error(data, e)
                except: pass
            results[name] = result
        return results

    def list(self) -> list:
        return list(self._plugins.keys())

    def get(self, name: str):
        return self._plugins.get(name)

    def clear(self):
        for p in list(self._plugins.values()):
            p.on_stop()
        self._plugins.clear()

    def stats(self) -> dict:
        return {"count": len(self._plugins), "plugins": list(self._plugins.keys()), "timeout": self._timeout}

manager = PluginManager()
"""V4-Local Plugin SDK — 标准化插件系统

符合 Document 3 Step 4 规范：
- PluginBase: on_init / on_event / on_result 标准接口
- PluginInput / PluginOutput Schema
- 插件上下文传递 (PluginContext)
- 沙箱隔离执行 (委托 sandbox.py)
- 版本管理
"""
import abc, logging, time, uuid
from typing import Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

# ─── Schema 标准 ───
@dataclass
class PluginInput:
    topic: str = ""
    data: dict = field(default_factory=dict)
    source: str = ""
    timestamp: float = 0.0

@dataclass
class PluginOutput:
    status: str = "success"   # success | fail | timeout
    result: dict = field(default_factory=dict)
    error: str = ""
    processing_ms: float = 0.0


# ─── 插件上下文 ───
@dataclass
class PluginContext:
    plugin_name: str = ""
    plugin_version: str = "0.1.0"
    config: dict = field(default_factory=dict)
    storage: dict = field(default_factory=dict)  # 插件间共享


# ─── 标准插件基类 ───
class BasePlugin(abc.ABC):
    """所有插件的标准基类"""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """插件唯一名称"""

    @property
    def version(self) -> str:
        return "0.1.0"

    def on_init(self, context: PluginContext):
        """插件初始化（启动时回调）"""
        self._ctx = context

    @abc.abstractmethod
    def on_event(self, event: dict) -> dict:
        """处理一条事件数据，返回处理结果 dict
        输入: PluginInput 格式的 dict
        输出: PluginOutput 格式的 dict
        """

    def on_result(self, result: dict):
        """结果回调（可选）"""
        pass

    def on_error(self, data: dict, error: Exception):
        logger.warning("Plugin %s error: %s", self.name, error)

    def on_stop(self):
        """插件停止时回调（可选）"""
        pass


# ─── 插件管理器 ───
class PluginManager:
    def __init__(self, sandbox_timeout: float = 10.0, use_sandbox: bool = False):
        self._plugins: dict[str, BasePlugin] = {}
        self._contexts: dict[str, PluginContext] = {}
        self._timeout = sandbox_timeout
        self._use_sandbox = use_sandbox

    @property
    def use_sandbox(self) -> bool:
        return self._use_sandbox

    @use_sandbox.setter
    def use_sandbox(self, value: bool):
        self._use_sandbox = value

    def register(self, plugin: BasePlugin, config: Optional[dict] = None):
        if plugin.name in self._plugins:
            logger.warning("Plugin %s already registered, replacing", plugin.name)
        ctx = PluginContext(
            plugin_name=plugin.name,
            plugin_version=plugin.version,
            config=config or {}
        )
        self._plugins[plugin.name] = plugin
        self._contexts[plugin.name] = ctx
        plugin.on_init(ctx)
        logger.info("Plugin registered: %s v%s", plugin.name, plugin.version)

    def unregister(self, name: str):
        if name in self._plugins:
            self._plugins[name].on_stop()
            del self._plugins[name]
            self._contexts.pop(name, None)

    def process(self, input_data: dict) -> dict[str, dict]:
        """用所有注册的插件处理一条数据
        input_data: PluginInput 格式 dict
        返回: { plugin_name: PluginOutput_dict }
        """
        results = {}
        for name, plugin in self._plugins.items():
            start = time.time()
            result = PluginOutput()
            try:
                # 沙箱模式
                if self._use_sandbox:
                    from .sandbox import run_in_sandbox
                    output = run_in_sandbox(plugin, input_data, timeout=self._timeout)
                    result = PluginOutput(**output)
                else:
                    # 直接执行
                    ret = plugin.on_event(input_data)
                    if isinstance(ret, dict):
                        result = PluginOutput(**ret) if "status" in ret else PluginOutput(result=ret)
                    else:
                        result.result = {"value": ret}
            except Exception as e:
                result.status = "fail"
                result.error = str(e)
                try:
                    plugin.on_error(input_data, e)
                except Exception:
                    pass
            result.processing_ms = round((time.time() - start) * 1000, 1)
            results[name] = asdict(result)
        return results

    def list(self) -> list[dict]:
        return [{"name": n, "version": p.version} for n, p in self._plugins.items()]

    def get(self, name: str) -> Optional[BasePlugin]:
        return self._plugins.get(name)

    def clear(self):
        for p in list(self._plugins.values()):
            p.on_stop()
        self._plugins.clear()
        self._contexts.clear()

    def stats(self) -> dict:
        return {
            "count": len(self._plugins),
            "plugins": list(self._plugins.keys()),
            "timeout": self._timeout,
            "sandbox": self._use_sandbox,
        }


# ── 全局单例 ──
manager = PluginManager()
