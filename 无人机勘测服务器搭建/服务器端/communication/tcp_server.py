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
        if self._loop: self._loop.call_soon_threadsafe(self._loop.stop)

    def _run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._serve())
        self._loop.close()

    async def _serve(self):
        cb = self._on_data
        class P(DeviceProtocol):
            def __init__(inner):
                DeviceProtocol.__init__(inner, on_data=cb)
        srv = await asyncio.start_server(P, self.host, self.port)
        print("  TCP listening on", self.host, ":", self.port)
        async with srv: await srv.serve_forever()

    def get_status(self):
        return {"running": self._server is not None, "host": self.host, "port": self.port}
