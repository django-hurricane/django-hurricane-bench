import json
import os
import random
import time
from locust import HttpUser, between, task


class DjangoHurricaneBenchUser(HttpUser):
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

    @task(30)
    def items_api_get(self):
        """Benchmark JSON API serialization of ORM queries."""
        offset = random.choice([0, 25, 50])
        self.client.get(
            f"/api/items?limit=25&offset={offset}",
            name="/api/items [GET]",
            timeout=15.0,
        )

    @task(25)
    def external_delay(self):
        """Benchmark non-blocking vs blocking handling of slow third-party API."""
        min_ms = random.randint(20, 40)
        max_ms = random.randint(50, 100)
        self.client.get(
            f"/external/fetch?min={min_ms}&max={max_ms}",
            name="/external/fetch [GET]",
            timeout=15.0,
        )

    @task(20)
    def catalog_render(self):
        """Benchmark Django Template Language (DTL) nested rendering engine."""
        limit = random.choice([15, 25])
        self.client.get(
            f"/catalog/render?limit={limit}",
            name="/catalog/render [GET]",
            timeout=15.0,
        )

    @task(15)
    def catalog_search(self):
        """Benchmark PostgreSQL relational filters, joins, and aggregates."""
        query = random.choice(["compute", "engine", "scale", "managed", "cloud"])
        self.client.get(
            f"/catalog/search?q={query}",
            name="/catalog/search [GET]",
            timeout=15.0,
        )

    @task(5)
    def items_api_post(self):
        """Benchmark JSON parsing, validation, and database insert."""
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
        """Re-verify session cookie authentication middleware."""
        with self.client.get("/api/auth/me", name="/api/auth/me [GET]", timeout=15.0, catch_response=True) as resp:
            if resp.status_code == 401:
                self._login()
                resp.failure("Session expired or missing - re-authenticating")
            else:
                resp.success()
