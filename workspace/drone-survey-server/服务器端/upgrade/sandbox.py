"""V4-Local 插件沙箱隔离模块

Windows 兼容版本：
- 插件隔离：subprocess + multiprocessing (Windows fallback: threading)
- 超时执行：threading + Event (Windows 兼容)
- 防崩溃：try/except 包围执行
"""
import threading, time, logging, traceback, sys

logger = logging.getLogger(__name__)

# ─── 模块级辅助函数（可 pickle） ───
def _sandbox_worker(plugin_module, plugin_class, input_data, result_container, index):
    """在子进程/线程中执行插件（模块级函数以便 pickle）"""
    try:
        import importlib
        mod = importlib.import_module(plugin_module)
        cls = getattr(mod, plugin_class)
        plugin = cls()
        output = plugin.on_event(input_data)
        result_container[index] = ("success", output, "")
    except Exception as e:
        result_container[index] = ("fail", None, str(e)[:200])

def _timeout_worker(func_path, args, kwargs, result_container, index):
    """模块级超时执行函数"""
    try:
        import importlib
        parts = func_path.rsplit(".", 1)
        mod = importlib.import_module(parts[0])
        func = getattr(mod, parts[1]) if len(parts) > 1 else mod
        # 如果 func_path 不是合法的模块路径，直接用 __main__
        ret = func(*args, **(kwargs or {}))
        result_container[index] = ("ok", ret, "")
    except Exception as e:
        result_container[index] = ("error", None, str(e))


def run_in_sandbox(plugin, input_data: dict, timeout: float = 10.0) -> dict:
    """在沙箱中执行插件 on_event

    Windows 上 fallback 为线程执行（无法完全隔离进程，
    但能捕获超时和异常）。
    """
    result = [None]
    thread = threading.Thread(
        target=_sandbox_worker,
        args=(plugin.__class__.__module__, plugin.__class__.__qualname__,
              input_data, result, 0),
        daemon=True
    )
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        logger.warning("Sandbox timeout: plugin %s exceeded %ss", plugin.name, timeout)
        return {"status": "timeout", "result": {}, "error": f"timeout (>={timeout}s)"}

    if result[0] is None:
        return {"status": "fail", "result": {}, "error": "sandbox internal error"}

    status, output, error = result[0]
    if status == "fail":
        return {"status": "fail", "result": {}, "error": error}
    return {"status": "success", "result": output if isinstance(output, dict) else {"value": output}, "error": ""}


def run_with_timeout(func, args=(), kwargs=None, timeout: float = 10.0) -> dict:
    """通用超时执行封装（线程模式，Windows 兼容）"""
    if kwargs is None:
        kwargs = {}

    result = [None]
    thread = threading.Thread(target=_timeout_exec, args=(func, args, kwargs, result, 0), daemon=True)
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        return {"status": "timeout", "error": f"timeout (>{timeout}s)"}

    if result[0] is None:
        return {"status": "fail", "error": "internal error"}

    status, ret, err = result[0]
    if status == "error":
        return {"status": "fail", "error": err}
    return {"status": "success", "result": ret}


def _timeout_exec(func, args, kwargs, result_container, index):
    """模块级超时执行内部函数"""
    try:
        ret = func(*args, **kwargs)
        result_container[index] = ("ok", ret, "")
    except Exception as e:
        result_container[index] = ("error", None, str(e))
