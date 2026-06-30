"""Locust 压测模板 — 测试服务器 API 性能

安装: pip install locust
启动: locust -f locustfile.py --host=http://localhost:8080
打开浏览器: http://localhost:8089
"""
from locust import HttpUser, task, between

class SurveyAPIUser(HttpUser):
    wait_time = between(0.5, 2.0)

    @task(3)
    def get_stats(self):
        self.client.get("/api/survey/stats")

    @task(2)
    def get_health(self):
        self.client.get("/api/health")

    @task(1)
    def get_devices(self):
        self.client.get("/api/survey/devices")

    @task(1)
    def get_circuit(self):
        self.client.get("/api/circuit-breaker/status")
