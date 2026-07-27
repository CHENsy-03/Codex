"""V2.0 TCP Server"""
import asyncio, time, threading

class DeviceProtocol(asyncio.Protocol):
    def __init__(self, on_data=None, on_connect=None, on_disconnect=None):
        self.transport = None; self.buffer = b""
        self.on_data = on_data; self.peer = ""

    def connection_made(self, transport):
        self.transport = transport
        if self.on_data is None: return
        self.peer = str(transport.get_extra_info("peername"))

    def data_received(self, data):
        self.buffer += data
        while len(self.buffer) >= 48:
            from communication.frame import unpack_frame
            r = unpack_frame(self.buffer)
            if r:
                h, p = r
                self.buffer = self.buffer[44 + h.payload_length + 4:]
                if self.on_data: self.on_data(self, h, p)
            else: self.buffer = self.buffer[1:]

    def send(self, data): 
        if self.transport: self.transport.write(data)

    def connection_lost(self, exc): pass


class TCPServer:
    def __init__(self, host="0.0.0.0", port=9000):
        self.host = host; self.port = port
        self._server = None; self._thread = None; self._loop = None
        self.clients = []; self._on_data = None

    def set_callbacks(self, on_data=None):
        self._on_data = on_data

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        try:
            if self._loop and self._loop.is_running():
                self._loop.call_soon_threadsafe(self._loop.stop)
        except Exception:
            pass

    def _run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._serve())
        except RuntimeError:
            pass
        try:
            self._loop.close()
        except Exception:
            pass

    async def _serve(self):
        import asyncio as _aio
        cb = self._on_data
        class P(DeviceProtocol):
            def __init__(inner):
                DeviceProtocol.__init__(inner, on_data=cb)
        try:
            srv = await asyncio.start_server(P, self.host, self.port)
            print("  [TCP] 监听中", self.host, ":", self.port)
            async with srv as server:
                self._server = server
                await srv.serve_forever()
        except (_aio.CancelledError, RuntimeError):
            pass
        finally:
            self._server = None

    def get_status(self):
        return {"running": self._server is not None, "host": self.host, "port": self.port}
