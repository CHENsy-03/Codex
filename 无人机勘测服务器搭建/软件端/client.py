"""MQTT survey client — runs on the board, publishes GPS data"""
import json, time, hmac, hashlib, logging
import paho.mqtt.client as mqtt

from crc import add_crc
from config import cfg
from gps import K803GNSS

logger = logging.getLogger(__name__)

TOPIC_DATA = f"survey/data/{cfg.device_id}"
TOPIC_RESP = f"survey/response/{cfg.device_id}"


def _on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("MQTT connected as %s", cfg.device_id)
        client.subscribe(TOPIC_RESP, qos=1)
    else:
        logger.error("MQTT connect failed: rc=%d", rc)


def _on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload)
        status = payload.get("status")
        if status == "success":
            logger.info("Survey accepted: %s", payload.get("batch_id"))
        elif status == "failed":
            logger.warning("Survey rejected: %s", payload.get("message"))
    except Exception as e:
        logger.error("Response error: %s", e)


def publish_survey(A, B, C, survey_time=None):
    """Publish one survey data point via MQTT QoS 1"""
    msg = add_crc({
        "device_id": cfg.device_id,
        "seq": int(time.time()),
        "survey_time": survey_time or int(time.time()),
        "A": A, "B": B, "C": C,
    })
    if cfg.hmac_key:
        payload_str = json.dumps(msg, sort_keys=True, separators=(",", ":"))
        msg["signature"] = hmac.new(
            cfg.hmac_key.encode(), payload_str.encode(), hashlib.sha256
        ).hexdigest()

    client = mqtt.Client(client_id=cfg.device_id, clean_session=False)
    if cfg.mqtt_user:
        client.username_pw_set(cfg.mqtt_user, cfg.mqtt_pass)
    client.on_connect = _on_connect
    client.on_message = _on_message
    client.connect(cfg.mqtt_host, cfg.mqtt_port, keepalive=60)
    client.loop_start()

    result = client.publish(TOPIC_DATA, json.dumps(msg), qos=1)
    time.sleep(0.5)  # wait for response
    client.loop_stop()
    client.disconnect()
    return result.rc == mqtt.MQTT_ERR_SUCCESS
