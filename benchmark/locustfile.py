import json
import os
import random
import time
from locust import HttpUser, between, task

# Conditionally activate step-up load shape unless explicitly disabled (e.g. during warmup)
if os.environ.get("USE_STEP_LOAD", "1").lower() in ("1", "true", "yes"):
    try:
        from shapes import StepLoadShape  # noqa: F401
    except ImportError:
        try:
            from benchmark.shapes import StepLoadShape  # noqa: F401
        except ImportError:
            pass


class BaseBenchUser(HttpUser):
    abstract = True
    wait_time = between(0.05, 0.25)

    def on_start(self):
        """Perform initial login to acquire session cookie and verify auth middleware."""
        for attempt in range(3):
            if self._login():
                break
            time.sleep(0.5)

    def _login(self):
        try:
            resp = self.client.post(
                "/api/auth/login",
                json={"username": "benchuser", "password": "benchpassword"},
                name="/api/auth/login",
                timeout=15.0,
            )
            return resp.status_code == 200
        except Exception:
            return False


_workload = os.environ.get("BENCH_WORKLOAD", "mixed").strip().lower()

if _workload == "gateway_aggregate":
    class DjangoHurricaneBenchUser(BaseBenchUser):
        @task
        def gateway_aggregate(self):
            sku = random.choice(["SKU-CLOUD-01", "SKU-NODE-02", "SKU-SCALE-03"])
            self.client.get(
                f"/api/gateway/aggregate?user_id=benchuser&sku={sku}",
                name="/api/gateway/aggregate [GET]",
                timeout=15.0,
            )

elif _workload == "external_fetch":
    class DjangoHurricaneBenchUser(BaseBenchUser):
        @task
        def external_delay(self):
            min_ms = random.randint(20, 40)
            max_ms = random.randint(50, 100)
            self.client.get(
                f"/external/fetch?min={min_ms}&max={max_ms}",
                name="/external/fetch [GET]",
                timeout=15.0,
            )

elif _workload == "catalog_render":
    class DjangoHurricaneBenchUser(BaseBenchUser):
        @task
        def catalog_render(self):
            limit = random.choice([15, 25])
            self.client.get(
                f"/catalog/render?limit={limit}",
                name="/catalog/render [GET]",
                timeout=15.0,
            )

elif _workload == "items_get":
    class DjangoHurricaneBenchUser(BaseBenchUser):
        @task
        def items_api_get(self):
            offset = random.choice([0, 25, 50])
            self.client.get(
                f"/api/items?limit=25&offset={offset}",
                name="/api/items [GET]",
                timeout=15.0,
            )

elif _workload == "items_post":
    class DjangoHurricaneBenchUser(BaseBenchUser):
        @task
        def items_api_post(self):
            payload = {
                "name": f"Locust Bench Item {random.randint(1000, 99999)}",
                "price": f"{round(random.uniform(19.99, 499.99), 2)}",
                "stock": random.randint(10, 100),
                "rating": round(random.uniform(3.0, 5.0), 1),
                "tags": ["locust", "bench", "synthetic"],
                "specifications": {"vcpus": "4", "ram": "16GB", "runner": "locust"},
            }
            self.client.post(
                "/api/items",
                json=payload,
                name="/api/items [POST]",
                timeout=15.0,
            )

elif _workload == "catalog_search":
    class DjangoHurricaneBenchUser(BaseBenchUser):
        @task
        def catalog_search(self):
            query = random.choice(["compute", "engine", "scale", "managed", "cloud"])
            self.client.get(
                f"/catalog/search?q={query}",
                name="/catalog/search [GET]",
                timeout=15.0,
            )

elif _workload == "auth":
    class DjangoHurricaneBenchUser(BaseBenchUser):
        @task(3)
        def auth_login(self):
            self._login()

        @task(7)
        def auth_me(self):
            self.client.get(
                "/api/auth/me",
                name="/api/auth/me [GET]",
                timeout=15.0,
            )

else:
    # Default: Mixed production workload
    class DjangoHurricaneBenchUser(BaseBenchUser):
        @task(25)
        def gateway_aggregate(self):
            sku = random.choice(["SKU-CLOUD-01", "SKU-NODE-02", "SKU-SCALE-03"])
            self.client.get(
                f"/api/gateway/aggregate?user_id=benchuser&sku={sku}",
                name="/api/gateway/aggregate [GET]",
                timeout=15.0,
            )

        @task(20)
        def items_api_get(self):
            offset = random.choice([0, 25, 50])
            self.client.get(
                f"/api/items?limit=25&offset={offset}",
                name="/api/items [GET]",
                timeout=15.0,
            )

        @task(15)
        def external_delay(self):
            min_ms = random.randint(20, 40)
            max_ms = random.randint(50, 100)
            self.client.get(
                f"/external/fetch?min={min_ms}&max={max_ms}",
                name="/external/fetch [GET]",
                timeout=15.0,
            )

        @task(15)
        def catalog_render(self):
            limit = random.choice([15, 25])
            self.client.get(
                f"/catalog/render?limit={limit}",
                name="/catalog/render [GET]",
                timeout=15.0,
            )

        @task(10)
        def catalog_search(self):
            query = random.choice(["compute", "engine", "scale", "managed", "cloud"])
            self.client.get(
                f"/catalog/search?q={query}",
                name="/catalog/search [GET]",
                timeout=15.0,
            )

        @task(5)
        def items_api_post(self):
            payload = {
                "name": f"Locust Bench Item {random.randint(1000, 99999)}",
                "price": f"{round(random.uniform(19.99, 499.99), 2)}",
                "stock": random.randint(10, 100),
                "rating": round(random.uniform(3.0, 5.0), 1),
                "tags": ["locust", "bench", "synthetic"],
                "specifications": {"vcpus": "4", "ram": "16GB", "runner": "locust"},
            }
            self.client.post(
                "/api/items",
                json=payload,
                name="/api/items [POST]",
                timeout=15.0,
            )

        @task(5)
        def auth_flow(self):
            with self.client.get("/api/auth/me", name="/api/auth/me [GET]", timeout=15.0, catch_response=True) as resp:
                if resp.status_code == 401:
                    self._login()
                    resp.failure("Session expired or missing - re-authenticating")
                else:
                    resp.success()

        @task(5)
        def auth_login_task(self):
            self._login()
