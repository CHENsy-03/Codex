import sys
with open("shard_db.py","rb") as f:
    data = bytearray(f.read())
old1 = b"""                    try:
                        prov_shard.conn.execute(f"INSERT INTO BLAH_BLAH_GPS ON CONFLICT DO NOTHING",
                            (r["batch_id"],r["region_code"],r["group_label"],r["lat"],r["lng"],r["alt"],r["e"],r["n"],r["u"],r["h"],r["v"],r["d"],r["is_correct"],r["device_id"],r["survey_time"],r["created_at"]))
                        ig += 1
                    except: pass"""
# ... etc
