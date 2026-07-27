"""MQTT 信号接收器"""
import json, logging, threading
logger = logging.getLogger(__name__)
class MQTTReceiver:
    def __init__(self, host="localhost", port=1883, topic="survey/data/+"):
        self.host, self.port, self.topic = host, port, topic
        self._client = None; self._running = False; self._callbacks = []
    def on_data(self, cb): self._callbacks.append(cb)
    def start(self):
        import paho.mqtt.client as mqtt
        self._client = mqtt.Client()
        self._client.on_message = self._on_msg
        self._client.connect(self.host, self.port, 60)
        self._client.subscribe(self.topic, qos=1)
        
        self._running = True
        threading.Thread(target=self._client.loop_forever, daemon=True).start()
        logger.info("MQTT receiver: %s:%d %s", self.host, self.port, self.topic)
    def _on_msg(self, client, userdata, msg):
        [cb(msg.payload.decode("utf-8")) for cb in self._callbacks]
    def stop():
        if self._client: self._client.disconnect()
