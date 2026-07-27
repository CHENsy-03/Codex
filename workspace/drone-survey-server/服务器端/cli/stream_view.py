"""V4-Local 实时流查看器

实时订阅 EventBus 事件流并在终端显示。
用法：
python -m cli.stream_view --topic gps.data
python -m cli.stream_view --all
"""
import argparse, threading, time, sys, os, json
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from upgrade.eventbus import Event, Topics, bus

def main():
    parser = argparse.ArgumentParser(description="实时事件流查看器")
    parser.add_argument("--topic", default="", help="过滤主题")
    parser.add_argument("--all", action="store_true", help="显示所有主题")
    parser.add_argument("--tail", type=int, default=50, help="显示历史条数")
    args = parser.parse_args()

    display_topic = args.topic or ("*" if args.all else "")

    print("📡 实时事件流查看器")
    print("   " + "-" * 40)
    print(f"   监听: {display_topic or 'gps.data'}")
    print(f"   历史显示: {args.tail} 条")
    print("   Ctrl+C 退出")
    print()

    received = [0]
    def on_event(event: Event):
        received[0] += 1
        ts = datetime.fromtimestamp(event.timestamp).strftime("%H:%M:%S.%f")[:12]
        src = event.source or "?"
        plen = len(json.dumps(event.payload))
        print(f"  [{ts}] {event.topic:<20} src={src:<12} id={event.id:<8} size={plen}B")
        if event.payload:
            items = "; ".join(f"{k}={v}" for k, v in list(event.payload.items())[:6])
            print(f"         └─ {items}")
        print()

    # 先回放历史
    if args.tail > 0:
        topic_filter = display_topic if display_topic and display_topic != "*" else ""
        events = bus.replay_all()
        count = 0
        for ev in reversed(events):
            if topic_filter and ev.topic != topic_filter:
                continue
            count += 1
            ts = datetime.fromtimestamp(ev.timestamp).strftime("%H:%M:%S.%f")[:12]
            print(f"  ↻ [{ts}] {ev.topic:<20} src={ev.source}")
            if count >= args.tail:
                break
        if count > 0:
            print(f"  ... 显示 {count} 条历史")
        print()

    # 订阅实时
    bus.subscribe(display_topic if display_topic else Topics.GPS_DATA, on_event)
    if display_topic == "*":
        bus.subscribe("*", on_event)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n👋 停止. 共接收 {received[0]} 条事件")
        bus.unsubscribe(display_topic if display_topic else Topics.GPS_DATA, on_event)

if __name__ == "__main__":
    main()
