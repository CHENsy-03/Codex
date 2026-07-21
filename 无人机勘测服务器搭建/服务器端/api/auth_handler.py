# -*- coding: utf-8 -*-
import time, hashlib, uuid
_tokens = {}
_users = {"admin": hashlib.sha256("admin123".encode()).hexdigest()}
def verify_token(token):
    return _tokens.get(token, {}).get("expire", 0) > time.time()
def handle_login(body):
    u = body.get("username",""); p = body.get("password","")
    pw_hash = hashlib.sha256(p.encode()).hexdigest()
    if u in _users and _users[u] == pw_hash:
        token = uuid.uuid4().hex
        _tokens[token] = {"username": u, "expire": time.time() + 7200}
        return 0, "success", {"token": token, "expire": 7200}
    return 1001, "auth failed", None
