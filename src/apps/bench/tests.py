import json
from decimal import Decimal
from django.contrib.auth.models import User
from django.test import AsyncClient, Client, TestCase
from apps.bench.models import Category, Product


class BenchmarkViewsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="benchuser",
            password="benchpassword",
            email="benchuser@example.com",
        )
        self.category = Category.objects.create(
            name="Cloud Compute",
            slug="cloud-compute",
            description="Cloud compute testing category",
        )
        self.product = Product.objects.create(
            category=self.category,
            sku="SKU-TEST-001",
            name="Elastic Node 1",
            description="Testing node instance",
            price=Decimal("49.99"),
            stock=25,
            rating=4.8,
            tags=["cloud", "test"],
            specifications={"vcpus": "4", "ram": "16GB"},
            is_active=True,
        )
        self.client = Client()

    def test_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")

    def test_catalog_render(self):
        response = self.client.get("/catalog/render")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enterprise Product Showcase")
        self.assertContains(response, "Elastic Node 1")

    def test_auth_sync(self):
        from apps.bench.views import auth_login_sync
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.post(
            "/api/auth/login",
            data=json.dumps({"username": "benchuser", "password": "benchpassword"}),
            content_type="application/json",
        )
        from django.contrib.sessions.middleware import SessionMiddleware
        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(request)
        request.session.save()

        response = auth_login_sync(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(data["status"], "authenticated")
        self.assertEqual(data["username"], "benchuser")

    def test_items_api_sync(self):
        from apps.bench.views import items_api_sync
        from django.test import RequestFactory
        factory = RequestFactory()

        # GET
        request_get = factory.get("/api/items")
        response_get = items_api_sync(request_get)
        self.assertEqual(response_get.status_code, 200)
        data_get = json.loads(response_get.content.decode("utf-8"))
        self.assertGreaterEqual(data_get["total"], 1)

        # POST
        payload = {
            "name": "New Benchmark Item",
            "sku": "SKU-NEW-002",
            "category_id": self.category.id,
            "price": "79.50",
            "stock": 10,
            "rating": 4.5,
            "tags": ["new", "test"],
            "specifications": {"vcpus": "2"},
        }
        request_post = factory.post(
            "/api/items",
            data=json.dumps(payload),
            content_type="application/json",
        )
        response_post = items_api_sync(request_post)
        self.assertEqual(response_post.status_code, 201)
        data_post = json.loads(response_post.content.decode("utf-8"))
        self.assertEqual(data_post["sku"], "SKU-NEW-002")

    def test_catalog_search_sync(self):
        from apps.bench.views import catalog_search_sync
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get("/catalog/search?q=Node")
        response = catalog_search_sync(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(data["aggregates"]["total_items"], 1)
        self.assertEqual(len(data["results"]), 1)

    async def test_async_views(self):
        from apps.bench.views import (
            auth_me_async,
            catalog_render_async,
            catalog_search_async,
            items_api_async,
        )
        from django.test import RequestFactory
        factory = RequestFactory()

        # Test items_api_async GET
        request_get = factory.get("/api/items")
        response_get = await items_api_async(request_get)
        self.assertEqual(response_get.status_code, 200)
        data_get = json.loads(response_get.content.decode("utf-8"))
        self.assertGreaterEqual(data_get["total"], 1)

        # Test items_api_async POST
        payload = {
            "name": "Async Benchmark Item",
            "sku": "SKU-ASYNC-003",
            "category_id": self.category.id,
            "price": "129.99",
            "stock": 15,
            "rating": 4.9,
            "tags": ["async", "test"],
            "specifications": {"vcpus": "8"},
        }
        request_post = factory.post(
            "/api/items",
            data=json.dumps(payload),
            content_type="application/json",
        )
        response_post = await items_api_async(request_post)
        self.assertEqual(response_post.status_code, 201)
        data_post = json.loads(response_post.content.decode("utf-8"))
        self.assertEqual(data_post["sku"], "SKU-ASYNC-003")

        # Test catalog_search_async
        request_search = factory.get("/catalog/search?q=Node")
        response_search = await catalog_search_async(request_search)
        self.assertEqual(response_search.status_code, 200)
        data_search = json.loads(response_search.content.decode("utf-8"))
        self.assertEqual(data_search["aggregates"]["total_items"], 1)

        # Test catalog_render_async
        request_render = factory.get("/catalog/render")
        response_render = await catalog_render_async(request_render)
        self.assertEqual(response_render.status_code, 200)
        self.assertIn("Enterprise Product Showcase", response_render.content.decode("utf-8"))

        # Test auth_me_async (unauthenticated)
        request_me = factory.get("/api/auth/me")
        from django.contrib.auth.models import AnonymousUser
        request_me.user = AnonymousUser()
        response_me = await auth_me_async(request_me)
        self.assertEqual(response_me.status_code, 401)

        # Test auth_me_async (authenticated)
        request_me.user = self.user
        response_me_auth = await auth_me_async(request_me)
        self.assertEqual(response_me_auth.status_code, 200)
        data_me = json.loads(response_me_auth.content.decode("utf-8"))
        self.assertTrue(data_me["authenticated"])
        self.assertEqual(data_me["username"], "benchuser")

    def test_sync_session_thread_local(self):
        import threading
        from apps.bench.views import get_sync_session

        sessions = []
        def worker():
            s = get_sync_session()
            sessions.append(s)

        threads = [threading.Thread(target=worker) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Different threads must have distinct requests.Session instances
        self.assertEqual(len(set(sessions)), 3)

    def test_manager_resolution(self):
        from apps.bench.views import get_product_manager, get_category_manager
        prod_mgr = get_product_manager()
        cat_mgr = get_category_manager()
        self.assertIsNotNone(prod_mgr)
        self.assertIsNotNone(cat_mgr)
