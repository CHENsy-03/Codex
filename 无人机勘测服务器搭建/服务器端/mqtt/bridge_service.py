
"""MQTT bridge service 鈥?runs ON THE SERVER

Receives survey data from MQTT broker, processes via existing gateway.py,
and publishes results back.

Usage:
    from mqtt.bridge_service import SurveyBridge
    bridge = SurveyBridge()
    bridge.run()
"""

import json
import logging
import threading

import paho.mqtt.client as mqtt

from mqtt.crc import verify_message, SequenceTracker
from mqtt.config import MQTTConfig
from gateway import SurveyGateway
from monitor.metrics_collector import MetricsCollector
from plugins.base import auto_detect

logger = logging.getLogger(__name__)


class SurveyBridge:
    """MQTT 鈫?Gateway bridge: receives MQTT messages, calls gateway.process_survey()"""

    def __init__(self, mqtt_config=None, gateway=None):
        self.mqtt_cfg = mqtt_config or MQTTConfig(client_id="survey-bridge")
        self.gw = gateway or SurveyGateway()
        self.metrics = MetricsCollector.get_instance()
        self._trackers = {}  # device_id -> SequenceTracker
        self._client = self._build_client()

    def _build_client(self):
        client = mqtt.Client(
            client_id=self.mqtt_cfg.client_id,
            clean_session=True,
            protocol=mqtt.MQTTv311,
        )
        if self.mqtt_cfg.use_tls:
            ca = self.mqtt_cfg.ca_path or None
            cert = self.mqtt_cfg.cert_path or None
            key = self.mqtt_cfg.key_path or None
            if ca:
                client.tls_set(ca_certs=ca, certfile=cert, keyfile=key)
            else:
                client.tls_set()
        if self.mqtt_cfg.username:
            client.username_pw_set(self.mqtt_cfg.username, self.mqtt_cfg.password)
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        return client

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Bridge connected to %s", self.mqtt_cfg.broker_host)
            # Subscribe to all survey data topics
            client.subscribe("survey/data/#", qos=1)
        else:
            logger.error("Bridge connect failed: rc=%d", rc)

    def _on_message(self, client, userdata, msg):
        """Process incoming survey data 鈥?THIS IS THE ENTRY POINT"""
        try:
            payload = json.loads(msg.payload)
        except json.JSONDecodeError as e:
            logger.error("JSON parse error: %s", e)
            return  # QoS 1 will retry

        # 1. CRC integrity check
        if not verify_message(payload):
            logger.warning("CRC mismatch, discarding (QoS 1 will retry)")
            self.metrics.record_crc_fail(device_id)
            return

        device_id = payload.get("device_id", "unknown")

        # 2. Sequence gap detection
        seq = payload.get("seq", 0)
        if device_id not in self._trackers:
            self._trackers[device_id] = SequenceTracker()
        self.metrics.record_msg(device_id, seq)
        if gaps:
            for start, end in gaps:
                logger.warning("Missed seq %d-%d from %s, requesting retransmit", start, end, device_id)
                self.metrics.record_loss(device_id, start, end)
                self._request_retransmit(device_id, start, end)

        # 3. Extract survey data
        A = payload.get("A")
        B = payload.get("B")
        C = payload.get("C")
        if not all([A, B, C]):
            logger.warning("Incomplete survey data from %s", device_id)
            self._publish_response(device_id, {"status": "failed",
                                                "message": "Missing A/B/C data",
                                                "action": "RESET"})
            return

        # 4. Process via existing gateway
        try:
            ok, msg_text, result = self.gw.process_survey(
                device_id=device_id,
                A=A, B=B, C=C,
                batch_id=payload.get("batch_id"),
                survey_time=payload.get("survey_time"),
            )
            if ok:
                self.metrics.record_success(device_id)
                self._publish_response(device_id, {
                    "status": "success",
                    "batch_id": result.get("batch_id", ""),
                })
            else:
                self.metrics.record_failure(device_id)
                self._publish_response(device_id, {
                    "status": "failed",
                    "message": msg_text,
                    "action": "RESET",
                })
        except Exception as e:
            logger.error("process_survey error: %s", e, exc_info=True)
            self._publish_response(device_id, {
                "status": "error",
                "message": str(e),
            })

    def _process_json_payload(self, payload):
        """Process pre-parsed JSON (A/B/C format) from any source"""
        device_id = payload.get("device_id", "unknown")

        # CRC check
        if not verify_message(payload):
            logger.warning("CRC mismatch, discarding")
            self.metrics.record_crc_fail(device_id)
            return

        # Sequence tracking
        seq = payload.get("seq", 0)
        if device_id not in self._trackers:
            self._trackers[device_id] = SequenceTracker()
        gaps = self._trackers[device_id].check(seq)
        self.metrics.record_msg(device_id, seq)
        if gaps:
            for start, end in gaps:
                logger.warning("Missed seq %d-%d from %s", start, end, device_id)
                self.metrics.record_loss(device_id, start, end)
                self._request_retransmit(device_id, start, end)

        # Extract A/B/C
        A = payload.get("A")
        B = payload.get("B")
        C = payload.get("C")
        if not all([A, B, C]):
            logger.warning("Incomplete survey data from %s", device_id)
            self._publish_response(device_id, {"status": "failed",
                                                "message": "Missing A/B/C data",
                                                "action": "RESET"})
            return

        # Process via gateway
        try:
            ok, msg_text, result = self.gw.process_survey(
                device_id=device_id, A=A, B=B, C=C,
                batch_id=payload.get("batch_id"),
                survey_time=payload.get("survey_time"),
            )
            if ok:
                self.metrics.record_success(device_id)
                self._publish_response(device_id, {
                    "status": "success",
                    "batch_id": result.get("batch_id", ""),
                })
            else:
                self.metrics.record_failure(device_id)
                self._publish_response(device_id, {
                    "status": "failed", "message": msg_text, "action": "RESET",
                })
        except Exception as e:
            logger.error("process_survey error: %s", e, exc_info=True)
            self._publish_response(device_id, {"status": "error", "message": str(e)})

    # Buffer for accumulating single-position fixes into A/B/C
    _fix_buffer = {}  # device_id -> [fix, fix, fix]

    def _process_single_fix(self, fix: dict, device_id: str = "unknown"):
        """Accumulate single position fixes (from NMEA/BESTPOS) into groups of 3

        Each fix is a dict with lat/lng/alt/h/v/d fields.
        When 3 fixes accumulate, calls process_survey() with A/B/C.
        """
        # Ensure position data exists
        if not fix or "lat" not in fix:
            return

        # Default H/V/D if not provided by parser
        fix.setdefault("h", 150.0)
        fix.setdefault("v", 200.0)
        fix.setdefault("d", 250.0)
        fix.setdefault("alt", 0.0)

        # Accumulate
        if device_id not in self._fix_buffer:
            self._fix_buffer[device_id] = []
        self._fix_buffer[device_id].append(fix)

        # When we have 3 fixes, dispatch
        if len(self._fix_buffer[device_id]) >= 3:
            fixes = self._fix_buffer[device_id][-3:]  # take last 3
            self._fix_buffer[device_id] = []  # reset buffer

            survey_time = fixes[0].get("survey_time", 0) or int(time.time())

            try:
                ok, msg_text, result = self.gw.process_survey(
                    device_id=device_id,
                    A=fixes[0], B=fixes[1], C=fixes[2],
                    survey_time=survey_time,
                )
                if ok:
                    self.metrics.record_success(device_id)
                    self._publish_response(device_id, {
                        "status": "success",
                        "batch_id": result.get("batch_id", ""),
                    })
                else:
                    self.metrics.record_failure(device_id)
                    self._publish_response(device_id, {
                        "status": "failed", "message": msg_text, "action": "RESET",
                    })
                    # Clear buffer on failure so next readings start fresh
                    self._fix_buffer[device_id] = []
            except Exception as e:
                logger.error("single fix error: %s", e, exc_info=True)
                self._publish_response(device_id, {"status": "error", "message": str(e)})
                self._fix_buffer[device_id] = []

    def _publish_response(self, device_id, data):
        """Publish result back to the device"""
        topic = f"survey/response/{device_id}"
        self._client.publish(topic, json.dumps(data), qos=1)

    def _request_retransmit(self, device_id, seq_from, seq_to):
        """Request retransmission of missed packets"""
        self.metrics.record_retransmit(device_id)
        topic = f"survey/retransmit/{device_id}"
        self._client.publish(topic, json.dumps({
            "action": "retransmit",
            "from": seq_from,
            "to": seq_to,
        }), qos=1)

    # 鈹€鈹€ Public API 鈹€鈹€

    def run(self, host=None, port=None):
        """Connect and start the bridge (blocking, Ctrl+C to stop)"""
        self._running = True
        self._client.connect(
            host or self.mqtt_cfg.broker_host,
            port or self.mqtt_cfg.broker_port,
            keepalive=self.mqtt_cfg.keepalive,
        )
        try:
            while self._running:
                self._client.loop(timeout=1.0)
        except KeyboardInterrupt:
            pass
        finally:
            self._running = False
            logger.info("Bridge stopping, flushing pending data...")
            # Cannot flush shard buffers here (they're in gateway calls)
            # but MQTT disconnect will clean up pending messages
            self._client.disconnect()

    def stop(self):
        """Request graceful shutdown (non-blocking)"""
        self._running = False

    def start_background(self):
        """Start bridge in background thread (non-blocking)"""
        t = threading.Thread(target=self.run, daemon=True)
        t.start()
        return t
