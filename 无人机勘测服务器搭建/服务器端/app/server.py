# -*- coding: utf-8 -*-
"""勘测系统服务器 V2.1 — 主入口 (clean)"""
import sys, os, time, argparse, threading, socket
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from typing import Optional
_gateway_ref = None; _worker_pool_ref = None; _sync_engine_ref = None; _db_ref = None
_resend_ref = None; _netmgr_ref = None; _devmgr_ref = None; _backup_scheduler_ref = None
_rest_server_ref = None; _ws_server_ref = None

def startup_check(config) -> bool:
    print(); print("="*55); print("  无人机勘测服务器 V2.0 - 启动检查"); print("="*55)
    checks = []
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
    checks.append(("Python 版本", py_ver >= "3.12", py_ver))
    checks.append(("配置文件", os.path.exists("config/server.yaml"), "config/server.yaml"))
    try: import duckdb; checks.append(("DuckDB", True, duckdb.__version__))
    except ImportError: checks.append(("DuckDB", False, "未安装"))
    try: import google.protobuf; checks.append(("Protobuf", True, google.protobuf.__version__))
    except ImportError: checks.append(("Protobuf", False, "未安装"))
    try: import yaml; checks.append(("PyYAML", True, yaml.__version__))
    except ImportError: checks.append(("PyYAML", False, "未安装"))
    db_dir = os.path.dirname(config.database.path)
    if db_dir: os.makedirs(db_dir, exist_ok=True)
    checks.append(("数据库目录", os.path.exists(db_dir) if db_dir else True, db_dir or "N/A"))
    os.makedirs(config.database.temp_directory, exist_ok=True)
    checks.append(("临时目录", os.path.exists(config.database.temp_directory), config.database.temp_directory))
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(0.5)
        free = s.connect_ex((config.host or "0.0.0.0", config.port)) != 0; s.close()
        checks.append(("通信端口", free, f"端口 {config.port} {'空闲' if free else '已被占用!'}"))
    except Exception: checks.append(("通信端口", True, f"端口 {config.port} (跳过检查)"))
    for name, ok, detail in checks:
        print(f"  [{'OK' if ok else 'FAIL'}] {name}: {detail}")
    all_ok = all(ok for _, ok, _ in checks)
    print(); print("  全部检查通过" if all_ok else "  部分检查失败, 请修复后重试"); return all_ok

def _settings_menu(config, db):
    global _gateway_ref, _resend_ref, _netmgr_ref, _devmgr_ref, _backup_scheduler_ref
    global _rest_server_ref, _ws_server_ref
    level_names = {"county":"县级","city":"市级","province":"省级","center":"总服务器"}
    while True:
        print(); print("="*55); print("  系统设置"); print("="*55)
        gw_mark = "[ON]" if (_gateway_ref and _gateway_ref.is_running) else "[OFF]"
        print(f"  1. {gw_mark} 设备网关 Gateway (端口 {config.port})")
        print(f"  2. 同步到上级 (上级ID: {config.sync.upstream_id or '未配置'})")
        print("  3. 数据库维护 (索引/VACUUM)")
        resend_mark = "[ON]" if _resend_ref else "[OFF]"
        print(f"  4. {resend_mark} 重传引擎 Resend")
        netmgr_mark = "[ON]" if _netmgr_ref else "[OFF]"
        print(f"  5. {netmgr_mark} 网络管理 NetworkManager")
        print("  6. 工作线程池状态"); print("  7. 导出数据到 CSV")
        print("  8. 设备管理 (注册/在线/固件)"); print("  9. 消息类型列表")
        bkp_mark = "[ON]" if _backup_scheduler_ref else "[OFF]"
        print(f"  10. {bkp_mark} 数据库定时备份"); print("  11. 版本升级检查")
        rest_mark = "[ON]" if _rest_server_ref else "[OFF]"
        ws_mark = "[ON]" if _ws_server_ref else "[OFF]"
        print(f"  12. {rest_mark} 启动/停止 REST API 服务器 (8080)")
        print(f"  13. {ws_mark} 启动/停止 WebSocket 服务器 (8081)")
        print("  14. 插件管理 (注册/沙箱)"); print("  0. 返回主菜单")
        choice = input("\n请选择: ").strip()
        if choice == "0": break
        elif choice == "1":
            if _gateway_ref is None:
                print(f"\n  正在启动 Gateway (0.0.0.0:{config.port})...")
                try:
                    from communication.gateway import DeviceGateway
                    from communication.session import SessionManager
                    from communication.ack_manager import AckManager
                    gw = DeviceGateway(server_id=config.id, host=config.host, port=config.port); gw.set_db(db)
                    sm = SessionManager(); sm.set_db(db); gw.set_session_manager(sm)
                    ack = AckManager(); ack.set_db(db); gw.set_ack_manager(ack)
                    def on_data(did, d): db.insert_gnss(d)
                    gw.set_on_data(on_data); gw.start(); _gateway_ref = gw
                    if _resend_ref is None:
                        from communication.resend import ResendManager
                        rm = ResendManager(max_retries=3, scan_interval=1.0); rm.set_db(db); rm.start(); _resend_ref = rm
                    if _netmgr_ref is None:
                        from network_manager.manager import NetworkManager
                        nm = NetworkManager(primary="4g"); nm.start(); _netmgr_ref = nm
                    from storage.init_config import is_first_run, run_wizard
                    if is_first_run("config/server.yaml"): run_wizard("config/server.yaml")
                    from communication.recovery import SessionRecovery
                    SessionRecovery(db=db, session_mgr=sm, ack_mgr=ack, gateway=gw).execute()
                    if _devmgr_ref is None:
                        from device.device_manager import DeviceManager
                        dm = DeviceManager(); dm.set_db(db)
                        gw.set_on_connect(lambda did, addr: dm.set_online(did, addr))
                        gw.set_on_disconnect(lambda did: dm.set_offline(did)); _devmgr_ref = dm
                    print(f"  Gateway 已启动: 0.0.0.0:{config.port}")
                except Exception as ex: print(f"  启动失败: {ex}")
            else:
                try: _gateway_ref.stop()
                except Exception: pass
                _gateway_ref = None
                if _resend_ref: _resend_ref.stop(); _resend_ref = None
                if _netmgr_ref: _netmgr_ref.stop(); _netmgr_ref = None
                print("  Gateway 已停止")
        elif choice == "2":
            global _sync_engine_ref
            if not config.sync.upstream_id:
                print("  上级服务器 ID 未配置, 跳过同步")
            else:
                if _sync_engine_ref is None:
                    from cluster.sync import SyncEngine
                    _sync_engine_ref = SyncEngine(db=db, server_id=config.id,
                        upstream_id=config.sync.upstream_id,
                        batch_size=config.sync.batch_size, retry_max=config.sync.retry_max)
                eng = _sync_engine_ref
                pending = eng.get_pending_count()
                print(f"  待同步记录: {pending}")
                if pending > 0:
                    records = eng.get_sync_batch()
                    if records:
                        db.log_sync(config.id, config.sync.upstream_id, len(records), "ok")
                        eng.mark_synced(len(records))
                        print(f"  已同步 {len(records)} 条 -> {config.sync.upstream_id}")
        elif choice == "3":
            try: db.create_indexes(); db.vacuum(); print("  索引已创建, WAL 已清理")
            except Exception as ex: print(f"  操作失败: {ex}")
        elif choice == "4":
            if _resend_ref: st = _resend_ref.get_statistics(); print(f"\n  [Resend] 发送={st['total_sent']} ACK={st['total_acked']} 重传={st['total_retried']}")
            else: print("\n  重传引擎未启动")
        elif choice == "5":
            if _netmgr_ref: st = _netmgr_ref.get_status(); print(f"\n  [Network] 活跃={st['active_link']} 信号={st['signal_strength']}% 延迟={st['latency_ms']}ms")
            else: print("\n  网络管理未启动")
        elif choice == "6":
            if _worker_pool_ref: st = _worker_pool_ref.stats; print(f"\n  [Worker] 处理={st.get('processed',0)} 错误={st.get('errors',0)}")
            else: print("\n  工作线程池未启动")
        elif choice == "7":
            try: out = db.export_csv(); print(f"  已导出: {out}")
            except Exception as ex: print(f"  导出失败: {ex}")
        elif choice == "8":
            if _devmgr_ref: st = _devmgr_ref.get_statistics(); print(f"\n  [Device] 注册={st.total_registered} 在线={st.online_count}")
            else: print("\n  设备管理未启动")
        elif choice == "9":
            from message.messages import MessageFactory
            print("\n  [消息类型]"); [print(f"  {t['hex']} {t['name']}") for t in MessageFactory.all_types()]
        elif choice == "10":
            if _backup_scheduler_ref: print(f"\n  备份状态: {_backup_scheduler_ref.status}")
            else:
                from maintenance.backup import create_backup, BackupScheduler
                print("\n  1=立即备份 2=启动定时(6h) 0=返回")
                sub = input("选择: ").strip()
                if sub == "1": create_backup(); print("  备份完成")
                elif sub == "2": bs = BackupScheduler(interval_hours=6.0, keep=10); bs.start(); _backup_scheduler_ref = bs; print("  定时备份已启动")
        elif choice == "11":
            from maintenance.upgrade import check_upgrade, run_migrations
            info = check_upgrade(); print(f"\n  当前 v{info['current_version']} 最新 v{info['latest_version']}")
            if info['needs_upgrade'] and input("执行升级? (y/n): ").strip().lower() == "y":
                from maintenance.upgrade import create_pre_upgrade_backup; create_pre_upgrade_backup(); run_migrations()
        elif choice == "12":
            if _rest_server_ref is None:
                from api.server import RESTHandler; from http.server import HTTPServer
                srv = HTTPServer(("0.0.0.0", 8080), RESTHandler); srv.allow_reuse_address = True
                threading.Thread(target=srv.serve_forever, daemon=True).start(); _rest_server_ref = srv
                print("\n  REST API 已启动: http://127.0.0.1:8080/api/v1/")
            else:
                try: _rest_server_ref.shutdown(); _rest_server_ref.server_close()
                except Exception: pass
                _rest_server_ref = None; print("\n  REST API 已停止")
        elif choice == "13":
            if _ws_server_ref is None:
                from api.websocket import WSServer, WSHandler
                srv = WSServer(("0.0.0.0", 8081), WSHandler); _ws_server_ref = srv
                threading.Thread(target=srv.serve_forever, daemon=True).start()
                print("\n  WebSocket 已启动: ws://127.0.0.1:8081/api/ws/device")
            else:
                try: _ws_server_ref.shutdown(); _ws_server_ref.server_close()
                except Exception: pass
                _ws_server_ref = None; print("\n  WebSocket 已停止")
        elif choice == "14":
            import os as _os, importlib as _il
            plugins_dir = _os.path.join(_os.path.dirname(__file__), "..", "plugins")
            if _os.path.isdir(plugins_dir):
                plugins = sorted([f for f in _os.listdir(plugins_dir) if f.endswith('.py') and not f.startswith('_')])
                print(f"\n  已注册插件: {len(plugins)} 个")
                for i, p in enumerate(plugins, 1): print(f"  {i}. {p}")
            else: print("  plugins 目录不存在")
        else: print("  无效选择")
        input("\n按 Enter 继续...")

def _data_manage_submenu(db):
    while True:
        print(); print("="*55); print("  数据管理"); print("="*55)
        print("  1. 按设备ID删除  2. 清空全部GNSS  3. 清空离线队列  4. 查看备份  0. 返回")
        choice = input("\n请选择: ").strip()
        if choice == "0": break
        elif choice == "1":
            did = input("设备ID: ").strip()
            if did and input(f"确认删除 {did}? (yes/no): ").strip().lower() == "yes":
                db.conn.execute("DELETE FROM gnss_position WHERE device_id=?", (did,)); print(f"  {did} 已删除")
        elif choice == "2":
            if input("确认清空全部GNSS? (yes/no): ").strip().lower() == "yes":
                db.conn.execute("DELETE FROM gnss_position"); print("  已清空")
        elif choice == "3":
            if input("确认清空离线队列? (yes/no): ").strip().lower() == "yes":
                db.conn.execute("DELETE FROM offline_message"); print("  已清空")
        elif choice == "4":
            from maintenance.backup import list_backups
            backups = list_backups()
            if backups:
                for b in backups[:10]: print(f"  {b['name']} {b['size_mb']}MB {b['created']}")
            else: print("  暂无备份")
        else: print("  无效选择")
        input("\n按 Enter 继续...")

def interactive_menu():
    global _gateway_ref, _rest_server_ref, _ws_server_ref
    from config.config_loader import ConfigLoader; from storage.duckdb_manager import DuckDBManager
    from app.data_queries import data_query_menu
    config = ConfigLoader.load("config/server.yaml")
    if not startup_check(config): input("\n按 Enter 退出..."); return
    level_names = {"county":"县级","city":"市级","province":"省级","center":"总服务器"}
    with DuckDBManager(db_path=config.database.path, memory_limit=config.database.memory_limit, temp_directory=config.database.temp_directory) as db:
        while True:
            print(); print("="*55)
            print(f"  勘测系统 v2.0 | {config.name} ({level_names.get(config.level, config.level)})")
            print("="*55)
            print("  1. 查看系统状态"); print("  2. 数据查询与浏览 (分页/筛选)")
            print("  3. 协议解析测试 (GPGGA/BESTPOS)"); print("  4. 查看离线消息队列")
            print("  5. 服务器注册管理"); print("  6. 系统设置 (Gateway/同步/重传/网络)")
            print("  7. 系统健康检查 (CPU/RAM/Disk)"); print("  8. 设备模拟器 (批量注入测试数据)")
            print("  9. 数据管理 (删除/清空/备份)"); print("  0. 退出")
            choice = input("\n请输入选择: ").strip()
            if choice == "0":
                if _gateway_ref:
                    try: _gateway_ref.stop()
                    except Exception: pass
                if _rest_server_ref:
                    try: _rest_server_ref.shutdown(); _rest_server_ref.server_close()
                    except Exception: pass
                if _ws_server_ref:
                    try: _ws_server_ref.shutdown(); _ws_server_ref.server_close()
                    except Exception: pass
                print("退出系统"); break
            elif choice == "1":
                from maintenance.upgrade import get_version, check_upgrade
                ver = get_version(); upg = check_upgrade()
                upg_str = f" (需升级到 {upg['latest_version']})" if upg['needs_upgrade'] else ""
                print(f"\n  [系统状态]"); print(f"  服务器ID: {config.id}"); print(f"  版本: v{ver}{upg_str}")
                print(f"  名称: {config.name}"); print(f"  层级: {config.level}")
                print(f"  监听地址: {config.host}:{config.port}"); print(f"  数据库: {config.database.path}")
                print(f"  协议: {', '.join(config.protocol.supported)} v{config.protocol.version}")
                gw_str = "运行中" if (_gateway_ref and _gateway_ref.is_running) else "已停止"
                print(f"  Gateway: {gw_str}")
            elif choice == "2": data_query_menu(db)
            elif choice == "3":
                from protocol.parser import ProtocolDispatcher
                dp = ProtocolDispatcher(config.id)
                raw = input("\n输入 GPGGA 或 BESTPOS 报文: ").strip()
                if raw:
                    result = dp.parse(raw.encode())
                    if result:
                        print(f"\n  [解析成功] 类型={result.msg_type} 纬度={result.latitude:.8f} 经度={result.longitude:.8f} 高度={result.height:.4f}m")
                        db.insert_gnss(result); print("  已保存到数据库")
                    else: print("  无法解析该报文")
            elif choice == "4":
                msgs = db.get_pending_offline(limit=20)
                print(f"\n  [离线队列] 共 {len(msgs)} 条待发送")
                for m in msgs[:10]: print(f"  设备={m.get('device_id','?')} 序号={m.get('sequence','?')} 状态={m.get('status','?')}")
            elif choice == "5":
                servers = db.get_servers()
                print(f"\n  [注册服务器] 共 {len(servers)} 台")
                for s in servers: print(f"  {s.get('server_id','?'):<25} {s.get('server_name','?'):<12} [{s.get('level','?')}]")
            elif choice == "6": _settings_menu(config, db)
            elif choice == "7":
                from monitor.health import HealthChecker
                hc = HealthChecker(db, config.id); h = hc.check()
                print(f"\n  [健康检查] CPU={h.cpu_percent:.1f}% RAM={h.memory_percent:.1f}% Disk={h.disk_percent:.1f}% DB={h.db_records}")
            elif choice == "8":
                from protocol.parser import ProtocolDispatcher
                dp2 = ProtocolDispatcher(config.id)
                n_str = input("\n模拟设备数量 (默认 3): ").strip() or "3"
                try: n = int(n_str)
                except ValueError: n = 3
                gga = "$GPGGA,092750.000,3025.880631,N,12016.157907,E,1,15,0.9,58.68,M,0.0,M,,*4A"
                bp = "#BESTPOSA,COM1,0,60.0,FINESTEERING,2222,1.000,0,32,SOL_COMPUTED,PSRDIFF,30.880631,120.157907,58.6800,-16.2700,WGS84,0.003,0.006,0.009,,,0.000,0.000,0,0,0,0,0,,*"
                inserted = 0
                for k in range(n):
                    r = dp2.parse((gga if k%2==0 else bp).encode())
                    if r: r.device_id = f"SIM-{k+1:03d}"; r.server_id = config.id; r.gnss_time = int(time.time()); r.created_at = int(time.time()); db.insert_gnss(r); inserted += 1
                print(f"  已插入 {inserted}/{n} 条模拟数据")
            elif choice == "9": _data_manage_submenu(db)
            else: print("无效选择, 请重新输入")
            input("\n按 Enter 继续...")

def main():
    parser = argparse.ArgumentParser(description="勘测系统服务器 V2.1")
    parser.add_argument("--config", default="config/server.yaml", help="配置文件路径")
    args = parser.parse_args()
    interactive_menu()

if __name__ == "__main__":
    main()
