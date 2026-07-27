# -*- coding: utf-8 -*-
"""V2.0 Packet Replay - replay GPS messages from file into Gateway/DB.
Usage: python -m debug.packet_replay <file_path> [--interval 1.0] [--db]
"""
import sys, os, time, argparse, pathlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def strip_quotes(path: str) -> str:
    return path.strip().strip('"' + "'")

def load_messages(filepath: str) -> list:
    """Load GPS messages from file. Supports one-per-line and multi-line."""
    path = strip_quotes(filepath)
    p = pathlib.Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    raw = p.read_text(encoding='utf-8', errors='ignore')
    messages = []
    current = []
    for line in raw.split('\n'):
        line = line.strip()
        if not line:
            if current:
                messages.append('\n'.join(current))
                current = []
            continue
        if line.startswith('#') or line.startswith('$') or line.startswith('%'):
            if current:
                messages.append('\n'.join(current))
                current = []
        current.append(line)
    if current:
        messages.append('\n'.join(current))
    return messages

def replay_to_db(filepath: str, interval: float = 1.0, max_count: int = 0):
    """Replay messages directly into DuckDB."""
    from config.config_loader import ConfigLoader
    from storage.duckdb_manager import DuckDBManager
    from protocol.parser import ProtocolDispatcher
    config = ConfigLoader.load('config/server.yaml')
    db = DuckDBManager(db_path=config.database.path,
                       memory_limit=config.database.memory_limit,
                       temp_directory=config.database.temp_directory)
    db.connect()
    dp = ProtocolDispatcher(config.id)
    messages = load_messages(filepath)
    if max_count > 0:
        messages = messages[:max_count]
    total = len(messages)
    print(f"Loaded {total} messages from {filepath}")
    print(f"Interval: {interval}s  Target: DB ({config.id})")
    ok_count = 0
    fail_count = 0
    for i, msg in enumerate(messages):
        try:
            parsed = dp.parse(msg.encode('utf-8'))
            if parsed:
                parsed.device_id = f"replay-{i+1:04d}"
                parsed.server_id = config.id
                parsed.gnss_time = int(time.time())
                parsed.created_at = int(time.time())
                db.insert_gnss(parsed)
                ok_count += 1
                print(f"  [{i+1}/{total}] OK  type={parsed.msg_type} "
                      f"lat={parsed.latitude:.6f} lng={parsed.longitude:.6f}")
            else:
                fail_count += 1
                print(f"  [{i+1}/{total}] SKIP (parse failed)")
        except Exception as ex:
            fail_count += 1
            print(f"  [{i+1}/{total}] FAIL: {ex}")
        time.sleep(interval)
    db.disconnect()
    print(f"\nDone: {ok_count} ok, {fail_count} failed, {total} total")
    return ok_count, fail_count

def replay_to_gateway(filepath: str, host: str = "127.0.0.1", port: int = 9000,
                      interval: float = 1.0, max_count: int = 0):
    """Replay messages via TCP to a running Gateway."""
    import socket
    from communication.frame import FrameHeader, pack_frame
    messages = load_messages(filepath)
    if max_count > 0:
        messages = messages[:max_count]
    total = len(messages)
    print(f"Loaded {total} messages from {filepath}")
    print(f"Target: tcp://{host}:{port}  Interval: {interval}s")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((host, port))
        sock.settimeout(5.0)
        ok_count = 0
        fail_count = 0
        for i, msg in enumerate(messages):
            try:
                hdr = FrameHeader()
                hdr.device_id = f"replay-{i+1:04d}"
                hdr.msg_type = 0x0002
                hdr.sequence = i + 1
                hdr.session_id = 1
                hdr.timestamp = int(time.time())
                frame = pack_frame(hdr, msg.encode('utf-8'))
                sock.sendall(frame)
                ok_count += 1
                print(f"  [{i+1}/{total}] SENT  len={len(frame)}")
            except Exception as ex:
                fail_count += 1
                print(f"  [{i+1}/{total}] FAIL: {ex}")
            time.sleep(interval)
        print(f"\nDone: {ok_count} sent, {fail_count} failed, {total} total")
    except ConnectionRefusedError:
        print(f"ERROR: Cannot connect to {host}:{port}. Is Gateway running?")
        print("Start Gateway first: python main.py -> 6 -> 1")
    finally:
        sock.close()

def main():
    parser = argparse.ArgumentParser(description='V2.0 Packet Replay Tool')
    parser.add_argument('file', help='Path to GPS message file')
    parser.add_argument('--interval', type=float, default=1.0,
                        help='Interval between messages in seconds')
    parser.add_argument('--max', type=int, default=0,
                        help='Max messages to replay (0=all)')
    parser.add_argument('--db', action='store_true',
                        help='Replay directly to database (default: try Gateway)')
    parser.add_argument('--host', default='127.0.0.1',
                        help='Gateway host (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=9000,
                        help='Gateway port (default: 9000)')
    args = parser.parse_args()
    if args.db:
        replay_to_db(args.file, args.interval, args.max)
    else:
        replay_to_gateway(args.file, args.host, args.port, args.interval, args.max)

if __name__ == '__main__':
    main()
