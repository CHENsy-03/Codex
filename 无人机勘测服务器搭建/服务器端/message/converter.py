# -*- coding: utf-8 -*-
"""V2.1 Protobuf Message Converter - dict/GNSSData <-> protobuf GNSSPosition"""
from protocol.proto.gnss_pb2 import GNSSPosition
def to_protobuf(data) -> GNSSPosition:
    pool = get_msg_pool(100)
    msg = pool.acquire()
    if hasattr(data, 'to_dict'):
        d = data.to_dict()
    elif isinstance(data, dict):
        d = data
    else:
        return msg
    msg.device_id = str(d.get("device_id", ""))
    msg.msg_type = str(d.get("msg_type", ""))
    msg.latitude = float(d.get("latitude", 0))
    msg.longitude = float(d.get("longitude", 0))
    msg.height = float(d.get("height", 0))
    msg.solution_type = int(d.get("solution_type", 0))
    msg.diff_age = float(d.get("diff_age", 0))
    msg.station_id = str(d.get("station_id", ""))
    msg.source_channel = str(d.get("source_channel", ""))
    msg.gnss_time = int(d.get("gnss_time", 0))
    msg.e_accuracy = float(d.get("e_accuracy", 0))
    msg.n_accuracy = float(d.get("n_accuracy", 0))
    msg.u_accuracy = float(d.get("u_accuracy", 0))
    msg.server_id = str(d.get("server_id", ""))
    msg.created_at = int(d.get("created_at", 0))
    return msg
def from_protobuf(msg: GNSSPosition) -> dict:
    return {"device_id": msg.device_id, "msg_type": msg.msg_type,
            "latitude": msg.latitude, "longitude": msg.longitude,
            "height": msg.height, "solution_type": msg.solution_type,
            "diff_age": msg.diff_age, "station_id": msg.station_id,
            "source_channel": msg.source_channel, "gnss_time": msg.gnss_time,
            "e_accuracy": msg.e_accuracy, "n_accuracy": msg.n_accuracy,
            "u_accuracy": msg.u_accuracy, "server_id": msg.server_id,
            "created_at": msg.created_at}
from message.pool import get_msg_pool
