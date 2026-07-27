"""Board Client — 勘测设备主程序

适配硬件:
  - K803_EK0407 GNSS 模块 (串口)
  - CM510-71F 无线数据传输模块 (TCP/UDP)

工作流程:
  读取 GPS → 3次测量 → 扩展检查 → 上传 → 等待结果

运行:
  python main.py                    # 正常模式
  python main.py --demo             # 模拟模式(无硬件)
  python main.py --mode tcp         # 指定传输模式
  python main.py --transport tcp    # CM510-71F TCP 模式
"""
import sys, time, logging, argparse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def demo_survey(engine):
    """模拟勘测流程（无硬件）"""
    import random
    logger.info("DEMO MODE — 模拟定位数据")
    while True:
        fake = lambda: {
            "lat": round(30.0 + random.uniform(-0.02, 0.02), 6),
            "lng": round(120.5 + random.uniform(-0.02, 0.02), 6),
            "alt": round(50 + random.uniform(-5, 5), 2),
            "e": round(random.uniform(0.3, 2.0), 2),
            "n": round(random.uniform(0.3, 2.0), 2),
            "u": round(random.uniform(1.0, 4.0), 2),
            "pos_type": "NARROW_INT",
            "quality": 4,
            "source": "demo",
        }
        for label in ("A", "B", "C"):
            engine.ext_mgr.record_all(fake())
        ok, payload, log = engine.run_survey()
        # Override with fake data since no real reader
        payload["A"] = fake(); payload["B"] = fake(); payload["C"] = fake()
        payload["survey_time"] = int(time.time())
        if engine.transporter:
            engine.transporter.send(payload)
        for line in log:
            logger.info(line)
        time.sleep(getattr(engine.cfg, "survey_interval", 10))


def real_survey(engine):
    """真机勘测循环"""
    logger.info("REAL MODE — 等待 GNSS 定位...")
    while True:
        try:
            ok, payload, log = engine.run_survey()
            for line in log:
                logger.info(line)
            if not ok:
                logger.warning("本次勘测未通过，重新开始")
        except KeyboardInterrupt:
            raise
        except Exception as e:
            logger.error("勘测异常: %s", e)
        time.sleep(getattr(engine.cfg, "survey_interval", 10))


def main():
    parser = argparse.ArgumentParser(description="Survey Device Client")
    parser.add_argument("--demo", action="store_true", help="模拟模式（无硬件）")
    parser.add_argument("--mode", choices=["serial", "tcp", "udp"],
                        help="GNSS 读取模式 (默认使用 config)")
    parser.add_argument("--transport", choices=["mqtt", "tcp", "udp"],
                        help="传输模式 (默认使用 config)")
    args = parser.parse_args()

    # 延迟导入避免循环
    from config import cfg
    from gps_reader import create_reader
    from transporter import create_transporter
    from survey_engine import SurveyEngine

    # 创建传输通道
    transport_kwargs = {
        "device_id": cfg.device_id,
        "hmac_key": cfg.hmac_key,
    }
    transport_mode = args.transport or cfg.transport
    if transport_mode == "tcp" or transport_mode == "udp":
        transport_kwargs["host"] = cfg.cm510_host
        transport_kwargs["port"] = cfg.cm510_port
    elif transport_mode == "mqtt":
        transport_kwargs["host"] = cfg.mqtt_host
        transport_kwargs["port"] = cfg.mqtt_port
        transport_kwargs["user"] = cfg.mqtt_user
        transport_kwargs["password"] = cfg.mqtt_pass
        transport_kwargs["topic_data"] = cfg.mqtt_topic_survey
        transport_kwargs["topic_resp"] = cfg.mqtt_topic_response

    transporter = create_transporter(transport_mode, **transport_kwargs)
    try:
        transporter.connect()
    except Exception as e:
        logger.warning("Transport connect failed: %s", e)
        transporter = None

    # 创建 GNSS 读取器
    reader = None
    if not args.demo:
        gps_mode = args.mode or cfg.gps_mode
        reader_kwargs = {"timeout": cfg.gps_timeout}
        if gps_mode == "serial":
            reader_kwargs["port"] = cfg.gps_port
            reader_kwargs["baud"] = cfg.gps_baud
        elif gps_mode == "tcp":
            reader_kwargs["host"] = cfg.cm510_host
            reader_kwargs["port"] = cfg.cm510_port
        elif gps_mode == "udp":
            reader_kwargs["port"] = cfg.cm510_port
        try:
            reader = create_reader(gps_mode, **reader_kwargs)
            reader.connect()
        except Exception as e:
            logger.warning("GNSS reader connect failed: %s", e)
            reader = None

    # 创建勘测引擎
    engine = SurveyEngine(cfg, reader=reader, transporter=transporter)

    # 启动信息
    print("=" * 55)
    print("  勘测设备客户端")
    print("  设备:      %s" % cfg.device_id)
    print("  GNSS模式:  %s" % (args.mode or cfg.gps_mode))
    print("  传输模式:  %s" % transport_mode)
    if transporter:
        print("  传输地址:  %s:%s" % (
            getattr(transporter, "host", "?"),
            getattr(transporter, "port", "?")))
    if engine.ext_mgr._extensions:
        names = [e.name for e in engine.ext_mgr._extensions]
        print("  扩展检测:  %s" % ", ".join(names))
    print("=" * 55)

    if args.demo or not reader:
        if not args.demo:
            logger.info("无有效 GNSS 读取器，切换至模拟模式")
        demo_survey(engine)
    else:
        real_survey(engine)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("正在关闭...")
        sys.exit(0)
