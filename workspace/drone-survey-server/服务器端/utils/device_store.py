
"""Device registry: in-memory device store (for demo; replace with DB in prod)

In production, store in PostgreSQL/Redis:
  device_id -> {cert_fingerprint, region_code, operator_face_embedding, ...}
"""
_device_registry = {}


def register_device(device_id, region_code, cert_fingerprint="", face_embedding=None):
    _device_registry[device_id] = {
        "region_code": region_code,
        "cert_fingerprint": cert_fingerprint,
        "face_embedding": face_embedding,
        "active": True,
    }


def get_device(device_id):
    return _device_registry.get(device_id)


def check_cert(device_id, cert_fingerprint):
    dev = get_device(device_id)
    if not dev:
        return False
    if not dev["cert_fingerprint"]:
        return True  # no cert configured = skip
    return dev["cert_fingerprint"] == cert_fingerprint


def get_face_embedding(device_id):
    dev = get_device(device_id)
    if dev:
        return dev.get("face_embedding")
    return None


# Pre-register demo devices
register_device("HW2024001", "hangzhou", cert_fingerprint="cert_a1b2c3")
register_device("HW2024002", "hangzhou")
register_device("SX2024001", "shaoxing", cert_fingerprint="cert_d4e5f6")
