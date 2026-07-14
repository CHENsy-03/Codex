# -*- coding: utf-8 -*-
"""无人机勘测服务器 V2.0 - 主入口"""
import sys
import os
import argparse
import time
import threading
from typing import Optional
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_tcp_server_ref: Optional[object] = None
_worker_pool_ref: Optional[object] = None
_sync_engine_ref: Optional[object] = None
_db_ref: Optional[object] = None
_gateway_ref: Optional[object] = None
_resend_ref: Optional[object] = None
_netmgr_ref: Optional[object] = None
_devmgr_ref: Optional[object] = None

def startup_check(config) -> bool:
    """V2.0 系统启动检查"""
    print()
    print("=" * 55)
    print("  无人机勘测服务器 V2.0 - 启动检查")
    print("=" * 55)
    checks = []
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
    checks.append(("Python 版本", py_ver >= "3.12", py_ver))
    checks.append(("配置文件", os.path.exists("config/server.yaml"), "config/server.yaml"))
    try:
        import duckdb
        checks.append(("DuckDB", True, duckdb.__version__))
    except ImportError:
        checks.append(("DuckDB", False, "未安装"))
    try:
        import google.protobuf
        checks.append(("Protobuf", True, google.protobuf.__version__))
    except ImportError:
        checks.append(("Protobuf", False, "未安装"))
    try:
        import yaml
        checks.append(("PyYAML", True, yaml.__version__))
    except ImportError:
        checks.append(("PyYAML", False, "未安装"))
    db_dir = os.path.dirname(config.database.path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    checks.append(("数据库目录", os.path.exists(db_dir) if db_dir else True, db_dir or "N/A"))
    os.makedirs(config.database.temp_directory, exist_ok=True)
    checks.append(("临时目录", os.path.exists(config.database.temp_directory), config.database.temp_directory))
    for name, ok, detail in checks:
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {name}: {detail}")
    all_ok = all(ok for _, ok, _ in checks)
    if all_ok:
        print()
        print("  全部检查通过")
    else:
        print()
        print("  部分检查失败, 请修复后重试")
    return all_ok

def _tcp_data_callback(proto_obj, header, payload: bytes):
    """TCP 收到设备数据帧时的回调: 解析 -> 入库 -> ACK"""
    global _db_ref
    from protocol.parser import ProtocolDispatcher
    dp = ProtocolDispatcher()
    parsed = dp.parse(payload)
    if parsed and _db_ref:
        parsed.server_id = getattr(proto_obj, "peer", "unknown")
        try:
            _db_ref.insert_gnss(parsed)
        except Exception:
            pass
    try:
        from communication.frame import pack_frame
        from communication.frame import FrameHeader
        seq = getattr(header, "sequence", 0)
        sid = getattr(header, "session_id", 0)
        ack_hdr = FrameHeader()
        ack_hdr.msg_type = 0x0002
        ack_hdr.sequence = seq
        ack_hdr.session_id = sid
        ack = pack_frame(ack_hdr, b"\x01" if parsed else b"\x00")
        proto_obj.send(ack)
    except Exception:
        pass

def _run_sync(config, db) -> None:
    """执行一次同步到上级服务器"""
    global _sync_engine_ref
    if not config.sync.upstream_id:
        print("  上级服务器 ID 未配置, 跳过同步")
        return
    if _sync_engine_ref is None:
        from cluster.sync import SyncEngine
        _sync_engine_ref = SyncEngine(
            db=db,
            server_id=config.id,
            upstream_id=config.sync.upstream_id,
            batch_size=config.sync.batch_size,
            retry_max=config.sync.retry_max,
        )
    engine = _sync_engine_ref
    pending = engine.get_pending_count()
    print(f"  待同步记录: {pending}")
    if pending > 0:
        records = engine.get_sync_batch()
        if records:
            db.log_sync(config.id, config.sync.upstream_id, len(records), "ok")
            engine.mark_synced(len(records))
            print(f"  已同步 {len(records)} 条 -> {config.sync.upstream_id}")
    else:
        print("  无待同步数据")
    stats = engine.get_statistics()
    print(f"  累计: 成功={stats['synced']}  失败={stats['failed']}")

def _settings_menu(config, db) -> None:
    """设置子菜单: TCP Server / 同步 / 数据库维护 / Worker"""
    global _tcp_server_ref, _worker_pool_ref, _sync_engine_ref, _db_ref
    global _gateway_ref, _resend_ref, _netmgr_ref
    global _devmgr_ref
    while True:
        print()
        print("=" * 55)
        print("  系统设置")
        print("=" * 55)
        gw_running = _gateway_ref is not None and _gateway_ref.is_running
        gw_mark = "[ON]" if gw_running else "[OFF]"
        print(f"  1. {gw_mark} 设备网关 Gateway (端口 {config.port})")
        sync_id = config.sync.upstream_id or "未配置"
        print(f"  2. 同步到上级 (上级ID: {sync_id})")
        print("  3. 数据库维护 (索引/VACUUM)")
        resend_running = _resend_ref is not None
        resend_mark = "[ON]" if resend_running else "[OFF]"
        print(f"  4. {resend_mark} 重传引擎 Resend")
        netmgr_running = _netmgr_ref is not None
        netmgr_mark = "[ON]" if netmgr_running else "[OFF]"
        print(f"  5. {netmgr_mark} 网络管理 NetworkManager")
        print("  6. 工作线程池状态")
        print("  7. 导出数据到 CSV")
        print("  8. 设备管理 (注册/在线/固件)")
        print("  9. 消息类型列表")
        print("  0. 返回主菜单")
        choice = input("\n请选择: ").strip()
        if choice == "0":
            break
        elif choice == "1":
            if _gateway_ref is None:
                print(f"\n  正在启动 Gateway (0.0.0.0:{config.port})...")
                try:
                    from communication.gateway import DeviceGateway
                    from communication.session import SessionManager
                    from communication.ack_manager import AckManager
                    from communication.resend import ResendManager
                    from network_manager.manager import NetworkManager
                    # 创建 Gateway
                    gw = DeviceGateway(server_id=config.id, host=config.host, port=config.port)
                    gw.set_db(db)
                    # 创建并注入 Session 管理器
                    session_mgr = SessionManager()
                    session_mgr.set_db(db)
                    gw.set_session_manager(session_mgr)
                    # 创建并注入 ACK 管理器
                    ack_mgr = AckManager()
                    ack_mgr.set_db(db)
                    gw.set_ack_manager(ack_mgr)
                    # 设置数据回调：解析后的 GNSS 数据入库
                    def on_gnss_data(device_id, gnss_data):
                        try:
                            db.insert_gnss(gnss_data)
                        except Exception:
                            pass
                    gw.set_on_data(on_gnss_data)
                    # 创建 DeviceManager
                    if _devmgr_ref is None:
                        from device.device_manager import DeviceManager
                        dm = DeviceManager()
                        dm.set_db(db)
                        def on_dev_status(device_id, status):
                            pass
                        dm.set_on_status_change(on_dev_status)
                        gw.set_on_connect(lambda dev_id, addr: dm.set_online(dev_id, addr))
                        gw.set_on_disconnect(lambda dev_id: dm.set_offline(dev_id))
                        _devmgr_ref = dm
                    # 启动 Gateway
                    gw.start()
                    _gateway_ref = gw
                    # 同时启动 Resend 管理器
                    if _resend_ref is None:
                        rm = ResendManager(max_retries=3, scan_interval=1.0)
                        rm.set_db(db)
                        rm.start()
                        _resend_ref = rm
                    # 同时启动 NetworkManager
                    if _netmgr_ref is None:
                        nm = NetworkManager(primary="4g")
                        nm.start()
                        _netmgr_ref = nm
                    print(f"  Gateway 已启动: 0.0.0.0:{config.port}")
                except Exception as ex:
                    print(f"  启动失败: {ex}")
            else:
                # 停止 Gateway (连带停止 Resend + NetMgr)
                try:
                    _gateway_ref.stop()
                except Exception:
                    pass
                _gateway_ref = None
                if _resend_ref:
                    try:
                        _resend_ref.stop()
                    except Exception:
                        pass
                    _resend_ref = None
                if _netmgr_ref:
                    try:
                        _netmgr_ref.stop()
                    except Exception:
                        pass
                    _netmgr_ref = None
                print("  Gateway 已停止")
        elif choice == "2":
            _run_sync(config, db)
        elif choice == "3":
            print("\n  正在创建索引 & VACUUM...")
            try:
                db.create_indexes()
                db.vacuum()
                print("  数据库索引已创建, WAL 已清理")
            except Exception as ex:
                print(f"  操作失败: {ex}")
        elif choice == "4":
            if _resend_ref is not None:
                st = _resend_ref.get_statistics()
                print(f"\n  [重传引擎 Resend]")
                print(f"  总发送: {st['total_sent']}  已ACK: {st['total_acked']}")
                print(f"  重传次数: {st['total_retried']}  失败: {st['total_failed']}")
                print(f"  待确认: {st['pending_count']}")
                pending_list = _resend_ref.get_pending_list()
                if pending_list:
                    print(f"  待重传列表 (前10条):")
                    for p in pending_list[:10]:
                        print(f"    设备={p['device_id']} seq={p['sequence']} "
                              f"重试={p['retry_count']} 状态={p['status']}")
            else:
                print("\n  重传引擎未启动 (请先启动 Gateway)")

        elif choice == "5":
            if _netmgr_ref is not None:
                st = _netmgr_ref.get_status()
                print(f"\n  [网络管理 NetworkManager]")
                print(f"  活跃链路: {st['active_link']} (主: {st['primary']})")
                print(f"  信号强度: {st['signal_strength']}%")
                print(f"  延迟: {st['latency_ms']}ms")
                print(f"  运行时长: {st['uptime_seconds']}s")
                print(f"  切换次数: {st['switch_count']}")
                print(f"  发送: {st['bytes_sent']} B  接收: {st['bytes_received']} B")
                links = _netmgr_ref.get_all_links()
                if links:
                    print(f"  所有链路:")
                    for l in links:
                        mark = " *" if l['active'] else ""
                        print(f"    {l['type']}{mark} 信号={l['signal']}% 延迟={l['latency_ms']}ms")
            else:
                print("\n  网络管理未启动 (请先启动 Gateway)")

        elif choice == "6":
            if _worker_pool_ref is not None:
                st = _worker_pool_ref.stats
                print(f"\n  [工作线程池]")
                print(f"  已处理: {st.get('processed', 0)}")
                print(f"  错误: {st.get('errors', 0)}")
            else:
                print("\n  工作线程池未启动")
                start = input("  启动? (y/n): ").strip().lower()
                if start == "y":
                    from processing.worker import WorkerPool
                    wp = WorkerPool(num_workers=4, queue_size=1000)
                    def batch_handler(data):
                        from protocol.parser import ProtocolDispatcher
                        dp = ProtocolDispatcher()
                        raw = data if isinstance(data, bytes) else data.get("raw", b"")
                        parsed = dp.parse(raw)
                        if parsed and db:
                            db.insert_gnss(parsed)
                    wp.start(batch_handler)
                    _worker_pool_ref = wp
                    _db_ref = db
                    print("  工作线程池已启动 (4 线程)")
        elif choice == "7":
            path = input("\n  导出路径 (留空=默认): ").strip()
            try:
                out = db.export_csv(path=path if path else "")
                print(f"  已导出: {out}")
            except Exception as ex:
                print(f"  导出失败: {ex}")
        elif choice == "8":
            if _devmgr_ref is not None:
                stats = _devmgr_ref.get_statistics()
                print(f"\n  [设备管理]")
                print(f"  已注册: {stats.total_registered}  在线: {stats.online_count}")
                print(f"  离线: {stats.offline_count}  超时: {stats.timeout_count}")
                if stats.by_type:
                    print(f"  类型分布: {stats.by_type}")
                online = _devmgr_ref.list_online()
                if online:
                    print(f"  在线设备 ({len(online)}):")
                    for dev in online[:10]:
                        print(f"    {dev.device_id:<20} {dev.device_type.value:<12} "
                              f"fw={dev.firmware_version or '?'}")
                else:
                    print("  (无在线设备)")
            else:
                print("\n  设备管理未启动 (请先启动 Gateway)")

        elif choice == "9":
            from message.messages import MessageFactory
            print(f"\n  [消息类型定义]")
            print(f"  代码    名称        说明")
            print(f"  ------  ----------  ----")
            for t in MessageFactory.all_types():
                desc_map = {
                    "HEARTBEAT": "心跳", "GNSS": "定位数据",
                    "IMU": "惯性测量", "STATUS": "设备状态",
                    "FILE": "文件传输", "ACK": "确认",
                    "NACK": "否认", "CONFIG": "配置",
                    "COMMAND": "指令",
                }
                print(f"  {t['hex']}  {t['name']:<10} {desc_map.get(t['name'], '')}")
        else:
            print("  无效选择")
        input("\n按 Enter 继续...")

def interactive_menu() -> None:
    """V2.0 交互式命令行菜单"""
    global _tcp_server_ref, _worker_pool_ref, _sync_engine_ref, _db_ref
    from config.config_loader import ConfigLoader
    from storage.duckdb_manager import DuckDBManager
    config = ConfigLoader.load("config/server.yaml")
    if not startup_check(config):
        input("\n按 Enter 退出...")
        return
    with DuckDBManager(
        db_path=config.database.path,
        memory_limit=config.database.memory_limit,
        temp_directory=config.database.temp_directory,
    ) as db:
        _db_ref = db
        while True:
            print()
            print("=" * 55)
            print(f"  uav_server v2.0 | {config.name} ({config.level})")
            print("=" * 55)
            print("  1. 查看系统状态")
            print("  2. 查看数据库统计")
            print("  3. 协议解析测试 (GPGGA/BESTPOS)")
            print("  4. 查看离线消息队列")
            print("  5. 服务器注册管理")
            print("  6. 系统设置 (Gateway/同步/重传/网络)")
            print("  7. 系统健康检查 (CPU/RAM/Disk)")
            print("  8. 设备模拟器 (批量注入测试数据)")
            print("  0. 退出")
            choice = input("\n请输入选择: ").strip()
            if choice == "0":
                if _gateway_ref is not None:
                    try:
                        _gateway_ref.stop()
                    except Exception:
                        pass
                    _gateway_ref = None
                if _resend_ref is not None:
                    try:
                        _resend_ref.stop()
                    except Exception:
                        pass
                    _resend_ref = None
                if _netmgr_ref is not None:
                    try:
                        _netmgr_ref.stop()
                    except Exception:
                        pass
                    _netmgr_ref = None
                if _devmgr_ref is not None:
                    _devmgr_ref = None
                if _tcp_server_ref is not None:
                    try:
                        _tcp_server_ref.stop()
                    except Exception:
                        pass
                    _tcp_server_ref = None
                if _worker_pool_ref is not None:
                    try:
                        _worker_pool_ref.shutdown()
                    except Exception:
                        pass
                    _worker_pool_ref = None
                print("退出系统")
                break
            elif choice == "1":
                print()
                print("  [系统状态]")
                print(f"  服务器ID: {config.id}")
                print(f"  名称: {config.name}")
                print(f"  层级: {config.level}")
                print(f"  监听地址: {config.host}:{config.port}")
                print(f"  数据库: {config.database.path}")
                print(f"  内存限制: {config.database.memory_limit}")
                print(f"  协议: {', '.join(config.protocol.supported)}")
                print(f"  协议版本: v{config.protocol.version}")
                crc_str = "开启" if config.protocol.crc_enabled else "关闭"
                enc_str = "开启" if config.protocol.encrypt else "关闭"
                print(f"  CRC: {crc_str}  加密: {enc_str}")
                print(f"  上级服务器: {config.sync.upstream_id or '未配置'}")
                gw_str = "运行中" if (_gateway_ref and _gateway_ref.is_running) else "已停止"
                print(f"  Gateway: {gw_str}")
            elif choice == "2":
                sizes = db.get_table_sizes()
                print()
                print("  [数据库统计]")
                print(f"  GNSS 记录: {sizes.get('gnss_position', 0)}")
                print(f"  设备会话: {sizes.get('device_session', 0)}")
                print(f"  离线消息: {sizes.get('offline_message', 0)}")
                print(f"  注册服务器: {sizes.get('server_registry', 0)}")
                print(f"  同步日志: {sizes.get('sync_log', 0)}")
            elif choice == "3":
                from protocol.parser import ProtocolDispatcher
                dp = ProtocolDispatcher(config.id)
                raw = input("\n输入 GPGGA 或 BESTPOS 报文: ").strip()
                if raw:
                    result = dp.parse(raw.encode())
                    if result:
                        print()
                        print(f"  [解析成功] 类型={result.msg_type}")
                        print(f"  纬度={result.latitude:.8f} 经度={result.longitude:.8f}")
                        print(f"  高度={result.height:.4f}m")
                        print(f"  解类型={result.solution_type}")
                        print(f"  东向精度={result.e_accuracy:.2f}cm")
                        print(f"  北向精度={result.n_accuracy:.2f}cm")
                        print(f"  高度精度={result.u_accuracy:.2f}cm")
                        db.insert_gnss(result)
                        print("  已保存到数据库")
                    else:
                        print("  无法解析该报文")
            elif choice == "4":
                msgs = db.get_pending_offline(limit=20)
                print()
                print(f"  [离线队列] 共 {len(msgs)} 条待发送")
                if msgs:
                    for m in msgs[:10]:
                        print(f"  设备={m.get('device_id','?')} "
                              f"序号={m.get('sequence','?')} "
                              f"状态={m.get('status','?')}")
                else:
                    print("  (无离线消息)")
            elif choice == "5":
                servers = db.get_servers()
                print()
                print(f"  [注册服务器] 共 {len(servers)} 台")
                if servers:
                    for s in servers:
                        print(f"  {s.get('server_id','?'):<25} "
                              f"{s.get('server_name','?'):<12} "
                              f"[{s.get('level','?')}] "
                              f"{s.get('status','?')}")
                else:
                    print("  (无注册服务器)")
            elif choice == "6":
                _settings_menu(config, db)
            elif choice == "7":
                print()
                print("  [系统健康检查]")
                try:
                    from monitor.health import HealthChecker
                    hc = HealthChecker(db, config.id)
                    h = hc.check()
                    print(f"  CPU: {h.cpu_percent:.1f}%")
                    print(f"  RAM: {h.memory_percent:.1f}%")
                    print(f"  Disk: {h.disk_percent:.1f}%")
                    print(f"  数据库记录: {h.db_records}")
                    print(f"  运行时长: {h.uptime_seconds}s")
                    print(f"  Python: {h.python_version}")
                except Exception as ex:
                    print(f"  健康检查失败: {ex}")
            elif choice == "8":
                print()
                print("  [设备模拟器]")
                n_str = input("模拟设备数量 (默认 3): ").strip() or "3"
                try:
                    n = int(n_str)
                except ValueError:
                    n = 3
                from protocol.parser import ProtocolDispatcher
                dp2 = ProtocolDispatcher(config.id)
                gpgga = "$GPGGA,092750.000,3025.880631,N,12016.157907,E,1,15,0.9,58.68,M,0.0,M,,*4A"
                bestpos = "#BESTPOSA,COM1,0,60.0,FINESTEERING,2222,1.000,0,32,SOL_COMPUTED,PSRDIFF,30.880631,120.157907,58.6800,-16.2700,WGS84,0.003,0.006,0.009,,,0.000,0.000,0,0,0,0,0,,*"
                inserted = 0
                for k in range(n):
                    raw = (gpgga if k % 2 == 0 else bestpos).encode()
                    result = dp2.parse(raw)
                    if result:
                        result.device_id = f"SIM-{k+1:03d}"
                        result.server_id = config.id
                        result.gnss_time = int(time.time())
                        result.created_at = int(time.time())
                        db.insert_gnss(result)
                        inserted += 1
                    time.sleep(0.02)
                print(f"  已插入 {inserted}/{n} 条模拟数据")
            else:
                print("无效选择, 请重新输入")
            input("\n按 Enter 继续...")

def main() -> None:
    """CLI 入口"""
    parser = argparse.ArgumentParser(description="无人机勘测服务器 V2.0")
    parser.add_argument("--config", default="config/server.yaml", help="配置文件路径")
    parser.add_argument("--level", choices=["county","city","province","center"],
                        default="county", help="服务器层级")
    parser.add_argument("--tcp", action="store_true", help="启动时自动开启 TCP Server")
    args = parser.parse_args()
    interactive_menu()

if __name__ == "__main__":
    main()
