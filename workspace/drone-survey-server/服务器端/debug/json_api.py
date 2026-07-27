# -*- coding: utf-8 -*-
"""V2.0 JSON API - HTTP test and monitoring interface.
Usage: python -m debug.json_api [--port 8080]
Endpoints:
  GET  /api/health         Health check
  GET  /api/stats          System statistics
  GET  /api/devices        Device list
  GET  /api/messages       Recent GNSS records
  POST /api/simulate       Simulate message injection
  GET  /api/resend/stats   Resend engine stats
  GET  /api/network/status Network status
"""
import json, time, sys, os, argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _get_db():
    from config.config_loader import ConfigLoader
    from storage.duckdb_manager import DuckDBManager
    config = ConfigLoader.load('config/server.yaml')
    db = DuckDBManager(db_path=config.database.path,
                       memory_limit=config.database.memory_limit,
                       temp_directory=config.database.temp_directory)
    db.connect()
    return db, config

class APIHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, default=str).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        p = urlparse(self.path)
        path = p.path.rstrip('/')
        params = parse_qs(p.query)
        db, config = _get_db()
        try:
            if path == '/api/health':
                from monitor.health import HealthChecker
                hc = HealthChecker(db, config.id)
                h = hc.check()
                self._json({'status':'ok','server_id':config.id,
                            'cpu_percent':h.cpu_percent,
                            'memory_percent':h.memory_percent,
                            'disk_percent':h.disk_percent,
                            'db_records':h.db_records,
                            'uptime_seconds':h.uptime_seconds})
            elif path == '/api/stats':
                sizes = db.get_table_sizes()
                self._json({'server_id':config.id,'level':config.level,
                            'gnss_records':sizes.get('gnss_position',0),
                            'device_sessions':sizes.get('device_session',0),
                            'offline_messages':sizes.get('offline_message',0),
                            'registered_servers':sizes.get('server_registry',0),
                            'sync_logs':sizes.get('sync_log',0)})
            elif path == '/api/devices':
                from device.device_manager import DeviceManager
                dm = DeviceManager()
                stats = dm.get_statistics()
                online = dm.list_online()
                self._json({'total':stats.total_registered,
                            'online':stats.online_count,
                            'offline':stats.offline_count,
                            'devices':[{'id':d.device_id,'type':d.device_type.value,
                                        'fw':d.firmware_version,'status':d.status.value}
                                       for d in online]})
            elif path == '/api/messages':
                limit = int(params.get('limit',[20])[0])
                rows = db.query_gnss(limit=limit)
                self._json({'count':len(rows),
                            'messages':[{'id':r.get('id'),'device_id':r.get('device_id'),
                                         'msg_type':r.get('msg_type'),
                                         'latitude':r.get('latitude'),
                                         'longitude':r.get('longitude'),
                                         'height':r.get('height'),
                                         'created_at':r.get('created_at')}
                                        for r in rows]})
            elif path == '/api/resend/stats':
                from communication.resend import ResendManager
                rm = ResendManager()
                self._json(rm.get_statistics())
            elif path == '/api/network/status':
                from network_manager.manager import NetworkManager
                nm = NetworkManager(primary='4g')
                self._json(nm.get_status())
            else:
                self._json({'endpoints':[
                    'GET /api/health','GET /api/stats','GET /api/devices',
                    'GET /api/messages?limit=20','POST /api/simulate',
                    'GET /api/resend/stats','GET /api/network/status']})
        except Exception as ex:
            self._json({'error':str(ex)},500)
        finally:
            db.disconnect()
    def do_POST(self):
        p = urlparse(self.path)
        db, config = _get_db()
        try:
            if p.path.rstrip('/') == '/api/simulate':
                length = int(self.headers.get('Content-Length',0))
                body = self.rfile.read(length)
                data = json.loads(body.decode('utf-8'))
                raw = data.get('raw','')
                device_id = data.get('device_id','api-sim')
                from protocol.parser import ProtocolDispatcher
                dp = ProtocolDispatcher(config.id)
                parsed = dp.parse(raw.encode() if isinstance(raw,str) else raw)
                if parsed:
                    parsed.device_id = device_id
                    parsed.server_id = config.id
                    parsed.gnss_time = int(time.time())
                    parsed.created_at = int(time.time())
                    db.insert_gnss(parsed)
                    self._json({'status':'ok','msg_type':parsed.msg_type,
                                'latitude':parsed.latitude,
                                'longitude':parsed.longitude})
                else:
                    self._json({'status':'error','message':'parse failed'},400)
            else:
                self._json({'error':'not found'},404)
        except Exception as ex:
            self._json({'error':str(ex)},500)
        finally:
            db.disconnect()
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin','*')
        self.send_header('Access-Control-Allow-Methods','GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers','Content-Type')
        self.end_headers()

def main():
    parser = argparse.ArgumentParser(description='V2.0 JSON API Server')
    parser.add_argument('--port', type=int, default=8080, help='HTTP port')
    parser.add_argument('--host', default='0.0.0.0', help='Bind address')
    args = parser.parse_args()
    server = HTTPServer((args.host, args.port), APIHandler)
    print(f'JSON API listening on http://{args.host}:{args.port}')
    print('Endpoints: /api/health /api/stats /api/devices /api/messages /api/simulate')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nShutting down...')
        server.shutdown()

if __name__ == '__main__':
    main()
