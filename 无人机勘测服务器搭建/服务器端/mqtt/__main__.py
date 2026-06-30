"""MQTT Bridge runner - start this on the server side"""
import logging
from logging_config import setup as setup_logging
setup_logging("mqtt")
logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from mqtt.bridge_service import SurveyBridge
bridge = SurveyBridge()
print("Starting MQTT bridge...")
bridge.run()
