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


DICT_ATTACK_PATHS = [
    "/.env",
    "/.git/config",
    "/wp-login.php",
    "/wp-admin/install.php",
    "/xmlrpc.php",
    "/phpmyadmin/index.php",
    "/pma/index.php",
    "/actuator/health",
    "/.aws/credentials",
    "/admin.php",
    "/login.php",
    "/cgi-bin/test.cgi",
    "/eval-stdin.php",
    "/web.config",
    "/vendor/phpunit/phpunit/src/Util/PHP/eval-stdin.php",
    "/backup.sql",
    "/config.json",
    "/setup.php",
    "/mysql/admin",
    "/solr/admin/info/system",
    "/geoserver/web",
]


class BaseBenchUser(HttpUser):
    abstract = True
    wait_time = between(0.05, 0.25)

    def on_start(self):
        """Generate client IP header and perform initial authentication."""
        self._client_ip = f"10.{random.randint(1, 200)}.{random.randint(1, 250)}.{random.randint(1, 250)}"
        for attempt in range(3):
            if self._login():
                break
            time.sleep(0.5)

    def _login(self):
        try:
            headers = {"X-Forwarded-For": self._client_ip}
            resp = self.client.post(
                "/api/auth/login",
                json={"username": "benchuser", "password": "benchpassword"},
                headers=headers,
                name="/api/auth/login",
                timeout=15.0,
            )
            return resp.status_code == 200
        except Exception:
            return False


_workload = os.environ.get("BENCH_WORKLOAD", "mixed").strip().lower()

if _workload == "security_flood":
    class DjangoHurricaneBenchUser(BaseBenchUser):
        """
        Security Flood Workload:
        Simulates realistic production attack conditions: legitimate user traffic is mixed with
        a massive flood of dictionary attack scanner probes (Fast-404) and rate-limiting abuse (429).
        """

        # 1. Legitimate Django Views (35% total traffic)
        @task(15)
        def valid_gateway_aggregate(self):
            sku = random.choice(["SKU-CLOUD-01", "SKU-NODE-02", "SKU-SCALE-03"])
            headers = {"X-Forwarded-For": self._client_ip}
            self.client.get(
                f"/api/gateway/aggregate?user_id=benchuser&sku={sku}",
                headers=headers,
                name="/api/gateway/aggregate [GET]",
                timeout=15.0,
            )

        @task(10)
        def valid_items_api_get(self):
            offset = random.choice([0, 25, 50])
            headers = {"X-Forwarded-For": self._client_ip}
            self.client.get(
                f"/api/items?limit=25&offset={offset}",
                headers=headers,
                name="/api/items [GET]",
                timeout=15.0,
            )

        @task(5)
        def valid_catalog_render(self):
            headers = {"X-Forwarded-For": self._client_ip}
            self.client.get(
                "/catalog/render?limit=20",
                headers=headers,
                name="/catalog/render [GET]",
                timeout=15.0,
            )

        @task(5)
        def valid_catalog_search(self):
            query = random.choice(["compute", "engine", "scale"])
            headers = {"X-Forwarded-For": self._client_ip}
            self.client.get(
                f"/catalog/search?q={query}",
                headers=headers,
                name="/catalog/search [GET]",
                timeout=15.0,
            )

        # 2. Fast-404 Malicious Scanner Dictionary Attack (45% total traffic)
        @task(45)
        def fast_404_dictionary_probe(self):
            path = random.choice(DICT_ATTACK_PATHS)
            scanner_ip = f"198.51.100.{random.randint(1, 250)}"
            headers = {"X-Forwarded-For": scanner_ip}
            with self.client.get(
                path,
                headers=headers,
                name="Fast-404 [Dictionary Attack]",
                timeout=5.0,
                catch_response=True,
            ) as resp:
                if resp.status_code == 404:
                    resp.success()
                else:
                    resp.failure(f"Expected early 404, got {resp.status_code}")

        # 3. Rate-Limiting Flood Probe (20% total traffic)
        @task(20)
        def rate_limit_flood_probe(self):
            # Fixed abusive IP to quickly trigger 429 Too Many Requests
            abusive_ip = f"203.0.113.{random.randint(1, 3)}"
            headers = {"X-Forwarded-For": abusive_ip}
            with self.client.get(
                "/api/items?limit=5",
                headers=headers,
                name="Rate-Limiter [429 Flood]",
                timeout=5.0,
                catch_response=True,
            ) as resp:
                if resp.status_code in (429, 200):
                    resp.success()
                else:
                    resp.failure(f"Expected 429 or 200, got {resp.status_code}")

elif _workload == "baseline_valid":
    class DjangoHurricaneBenchUser(BaseBenchUser):
        """
        Baseline Valid Workload:
        100% legitimate traffic with identical server configuration, without the flood of
        nonsense requests. Used to establish clean baseline throughput and measure the
        exact performance penalty incurred during security flood attacks.
        """
        @task(25)
        def gateway_aggregate(self):
            sku = random.choice(["SKU-CLOUD-01", "SKU-NODE-02", "SKU-SCALE-03"])
            headers = {"X-Forwarded-For": self._client_ip}
            self.client.get(
                f"/api/gateway/aggregate?user_id=benchuser&sku={sku}",
                headers=headers,
                name="/api/gateway/aggregate [GET]",
                timeout=15.0,
            )

        @task(20)
        def items_api_get(self):
            offset = random.choice([0, 25, 50])
            headers = {"X-Forwarded-For": self._client_ip}
            self.client.get(
                f"/api/items?limit=25&offset={offset}",
                headers=headers,
                name="/api/items [GET]",
                timeout=15.0,
            )

        @task(15)
        def external_delay(self):
            min_ms = random.randint(20, 40)
            max_ms = random.randint(50, 100)
            headers = {"X-Forwarded-For": self._client_ip}
            self.client.get(
                f"/external/fetch?min={min_ms}&max={max_ms}",
                headers=headers,
                name="/external/fetch [GET]",
                timeout=15.0,
            )

        @task(15)
        def catalog_render(self):
            limit = random.choice([15, 25])
            headers = {"X-Forwarded-For": self._client_ip}
            self.client.get(
                f"/catalog/render?limit={limit}",
                headers=headers,
                name="/catalog/render [GET]",
                timeout=15.0,
            )

        @task(10)
        def catalog_search(self):
            query = random.choice(["compute", "engine", "scale", "managed", "cloud"])
            headers = {"X-Forwarded-For": self._client_ip}
            self.client.get(
                f"/catalog/search?q={query}",
                headers=headers,
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
            headers = {"X-Forwarded-For": self._client_ip}
            self.client.post(
                "/api/items",
                json=payload,
                headers=headers,
                name="/api/items [POST]",
                timeout=15.0,
            )

        @task(5)
        def auth_flow(self):
            headers = {"X-Forwarded-For": self._client_ip}
            with self.client.get(
                "/api/auth/me",
                headers=headers,
                name="/api/auth/me [GET]",
                timeout=15.0,
                catch_response=True,
            ) as resp:
                if resp.status_code == 401:
                    self._login()
                    resp.failure("Session expired or missing - re-authenticating")
                else:
                    resp.success()

        @task(5)
        def auth_login_task(self):
            self._login()

elif _workload == "gateway_aggregate":
    class DjangoHurricaneBenchUser(BaseBenchUser):
        @task
        def gateway_aggregate(self):
            sku = random.choice(["SKU-CLOUD-01", "SKU-NODE-02", "SKU-SCALE-03"])
            headers = {"X-Forwarded-For": self._client_ip}
            self.client.get(
                f"/api/gateway/aggregate?user_id=benchuser&sku={sku}",
                headers=headers,
                name="/api/gateway/aggregate [GET]",
                timeout=15.0,
            )

elif _workload == "external_fetch":
    class DjangoHurricaneBenchUser(BaseBenchUser):
        @task
        def external_delay(self):
            min_ms = random.randint(20, 40)
            max_ms = random.randint(50, 100)
            headers = {"X-Forwarded-For": self._client_ip}
            self.client.get(
                f"/external/fetch?min={min_ms}&max={max_ms}",
                headers=headers,
                name="/external/fetch [GET]",
                timeout=15.0,
            )

elif _workload == "catalog_render":
    class DjangoHurricaneBenchUser(BaseBenchUser):
        @task
        def catalog_render(self):
            limit = random.choice([15, 25])
            headers = {"X-Forwarded-For": self._client_ip}
            self.client.get(
                f"/catalog/render?limit={limit}",
                headers=headers,
                name="/catalog/render [GET]",
                timeout=15.0,
            )

elif _workload == "items_get":
    class DjangoHurricaneBenchUser(BaseBenchUser):
        @task
        def items_api_get(self):
            offset = random.choice([0, 25, 50])
            headers = {"X-Forwarded-For": self._client_ip}
            self.client.get(
                f"/api/items?limit=25&offset={offset}",
                headers=headers,
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
            headers = {"X-Forwarded-For": self._client_ip}
            self.client.post(
                "/api/items",
                json=payload,
                headers=headers,
                name="/api/items [POST]",
                timeout=15.0,
            )

elif _workload == "catalog_search":
    class DjangoHurricaneBenchUser(BaseBenchUser):
        @task
        def catalog_search(self):
            query = random.choice(["compute", "engine", "scale", "managed", "cloud"])
            headers = {"X-Forwarded-For": self._client_ip}
            self.client.get(
                f"/catalog/search?q={query}",
                headers=headers,
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
            headers = {"X-Forwarded-For": self._client_ip}
            self.client.get(
                "/api/auth/me",
                headers=headers,
                name="/api/auth/me [GET]",
                timeout=15.0,
            )

else:
    # Default: Mixed production workload
    class DjangoHurricaneBenchUser(BaseBenchUser):
        @task(25)
        def gateway_aggregate(self):
            sku = random.choice(["SKU-CLOUD-01", "SKU-NODE-02", "SKU-SCALE-03"])
            headers = {"X-Forwarded-For": self._client_ip}
            self.client.get(
                f"/api/gateway/aggregate?user_id=benchuser&sku={sku}",
                headers=headers,
                name="/api/gateway/aggregate [GET]",
                timeout=15.0,
            )

        @task(20)
        def items_api_get(self):
            offset = random.choice([0, 25, 50])
            headers = {"X-Forwarded-For": self._client_ip}
            self.client.get(
                f"/api/items?limit=25&offset={offset}",
                headers=headers,
                name="/api/items [GET]",
                timeout=15.0,
            )

        @task(15)
        def external_delay(self):
            min_ms = random.randint(20, 40)
            max_ms = random.randint(50, 100)
            headers = {"X-Forwarded-For": self._client_ip}
            self.client.get(
                f"/external/fetch?min={min_ms}&max={max_ms}",
                headers=headers,
                name="/external/fetch [GET]",
                timeout=15.0,
            )

        @task(15)
        def catalog_render(self):
            limit = random.choice([15, 25])
            headers = {"X-Forwarded-For": self._client_ip}
            self.client.get(
                f"/catalog/render?limit={limit}",
                headers=headers,
                name="/catalog/render [GET]",
                timeout=15.0,
            )

        @task(10)
        def catalog_search(self):
            query = random.choice(["compute", "engine", "scale", "managed", "cloud"])
            headers = {"X-Forwarded-For": self._client_ip}
            self.client.get(
                f"/catalog/search?q={query}",
                headers=headers,
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
            headers = {"X-Forwarded-For": self._client_ip}
            self.client.post(
                "/api/items",
                json=payload,
                headers=headers,
                name="/api/items [POST]",
                timeout=15.0,
            )

        @task(5)
        def auth_flow(self):
            headers = {"X-Forwarded-For": self._client_ip}
            with self.client.get(
                "/api/auth/me",
                headers=headers,
                name="/api/auth/me [GET]",
                timeout=15.0,
                catch_response=True,
            ) as resp:
                if resp.status_code == 401:
                    self._login()
                    resp.failure("Session expired or missing - re-authenticating")
                else:
                    resp.success()

        @task(5)
        def auth_login_task(self):
            self._login()
