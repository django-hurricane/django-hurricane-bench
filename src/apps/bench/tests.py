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
        from apps.bench.views import items_api_async, catalog_search_async
        from django.test import RequestFactory
        factory = RequestFactory()

        # Test items_api_async GET
        request_get = factory.get("/api/items")
        response_get = await items_api_async(request_get)
        self.assertEqual(response_get.status_code, 200)
        data_get = json.loads(response_get.content.decode("utf-8"))
        self.assertGreaterEqual(data_get["total"], 1)

        # Test catalog_search_async
        request_search = factory.get("/catalog/search?q=Node")
        response_search = await catalog_search_async(request_search)
        self.assertEqual(response_search.status_code, 200)
        data_search = json.loads(response_search.content.decode("utf-8"))
        self.assertEqual(data_search["aggregates"]["total_items"], 1)
