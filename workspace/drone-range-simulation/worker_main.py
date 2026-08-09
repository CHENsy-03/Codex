"""常驻 Worker 进程入口（TASK-008）。

仅作为极薄的进程入口：导入 app.worker_protocol 的 main 并执行。
不含地图算法、坐标算法或业务规则；不创建 QApplication、不导入
main_window.py / map_view.py、不打开网络端口、不连接数据库、不写业务文件。
"""

from app.worker_protocol import main

if __name__ == "__main__":
    raise SystemExit(main())
