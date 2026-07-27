"""V4 压力测试 — 向 API 发送批量请求"""
import urllib.request, json, time, random, sys

URL = "http://localhost:8080/api/survey/upload"

def gen_bestposa(seq_start=1000):
    lines = []
    for j in range(3):
        lat = 30.0 + random.uniform(-0.001, 0.001)
        lng = 120.5 + random.uniform(-0.001, 0.001)
        alt = 50 + random.uniform(-0.5, 0.5)
        lines.append(f"#BESTPOSA,COM1,0,60.0,FINESTEERING,2222,{seq_start+j:.3f},00000000,0000,1114;SOL_COMPUTED,NARROW_INT,{lat:.6f},{lng:.6f},{alt:.2f},1.0,WGS84,0.008,0.009,0.015,0008,0.05,0.05,8,6,1,1,0,0,0,0*0000")
    return "\n".join(lines)

def run(count=10):
    ok = 0; fail = 0; times = []
    for i in range(count):
        data = gen_bestposa(1000 + i * 3).encode()
        try:
            start = time.time()
            req = urllib.request.Request(URL, data=data, headers={"Content-Type": "text/plain"})
            resp = urllib.request.urlopen(req, timeout=5)
            elapsed = time.time() - start
            times.append(elapsed)
            r = json.loads(resp.read())
            if r.get("success") == r.get("total"): ok += 1
            else: fail += 1
        except: fail += 1
    avg_ms = sum(times) / len(times) * 1000 if times else 0
    print(f"结果: {ok}/{count} 通过, {fail} 失败")
    print(f"平均耗时: {avg_ms:.1f}ms")
    print(f"吞吐量: {count/(sum(times) if times else 1):.0f} req/s")

if __name__ == "__main__":
    c = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    run(c)
