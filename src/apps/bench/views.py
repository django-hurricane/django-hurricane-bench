import json
import os
import time
from decimal import Decimal
from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Max, Min, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt

import httpx
import requests
from apps.bench.models import Category, Product

IS_WSGI = os.environ.get("HURRICANE_MODE", "").lower() == "wsgi"
FORCE_SYNC_VIEWS = os.environ.get("FORCE_SYNC_VIEWS", "0").lower() in ("1", "true", "yes")

# ---------------------------------------------------------------------------
# Persistent Connection-Pooled HTTP Clients
# ---------------------------------------------------------------------------

_sync_session = None

def get_sync_session():
    global _sync_session
    if _sync_session is None:
        _sync_session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=50, pool_maxsize=200)
        _sync_session.mount("http://", adapter)
        _sync_session.mount("https://", adapter)
    return _sync_session


_async_client = None

def get_async_client():
    global _async_client
    if _async_client is None or _async_client.is_closed:
        _async_client = httpx.AsyncClient(
            timeout=15.0,
            limits=httpx.Limits(max_connections=200, max_keepalive_connections=50),
        )
    return _async_client


# Async template renderer utilizing threadpool for concurrent CPU dispatch
render_template_async = sync_to_async(render_to_string, thread_sensitive=False)

# ---------------------------------------------------------------------------
# 1. User Authentication (Login & Middleware Check)
# ---------------------------------------------------------------------------

@csrf_exempt
def auth_login_sync(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        data = request.POST

    username = data.get("username", "benchuser")
    password = data.get("password", "benchpassword")

    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        return JsonResponse({
            "status": "authenticated",
            "username": user.username,
            "session_key": request.session.session_key,
            "flavor": "wsgi",
        })
    return JsonResponse({"error": "Invalid credentials"}, status=401)


@csrf_exempt
async def auth_login_async(request):
    from django.contrib.auth import aauthenticate, alogin

    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        data = request.POST

    username = data.get("username", "benchuser")
    password = data.get("password", "benchpassword")

    user = await aauthenticate(request, username=username, password=password)
    if user is not None:
        await alogin(request, user)
        session_key = await request.session.asave() or request.session.session_key
        return JsonResponse({
            "status": "authenticated",
            "username": user.username,
            "session_key": session_key,
            "flavor": "asgi",
        })
    return JsonResponse({"error": "Invalid credentials"}, status=401)


def auth_me(request):
    """Verifies session and auth middleware validation."""
    if request.user.is_authenticated:
        return JsonResponse({
            "authenticated": True,
            "username": request.user.username,
            "email": request.user.email,
        })
    return JsonResponse({"authenticated": False}, status=401)


# ---------------------------------------------------------------------------
# 2. Complex Template Rendering (CPU / Template Engine Benchmark)
# ---------------------------------------------------------------------------

def catalog_render_sync(request):
    """Synchronous template rendering directly executed on WSGI worker thread."""
    limit = int(request.GET.get("limit", 25))
    products = list(
        Product.objects.filter(is_active=True)
        .select_related("category")
        .order_by("-created_at")[:limit]
    )

    categories = list(Category.objects.annotate(prod_count=Count("products")))
    total_stock = sum(p.stock for p in products)
    avg_price = (sum(p.price for p in products) / len(products)) if products else Decimal(0)
    top_rated = sorted(products, key=lambda p: p.rating, reverse=True)[:5]

    context = {
        "title": "Enterprise Product Showcase",
        "products": products,
        "categories": categories,
        "stats": {
            "displayed_count": len(products),
            "total_stock": total_stock,
            "avg_price": round(float(avg_price), 2),
            "top_rated": top_rated,
        },
        "mode": "ASGI-Sync" if FORCE_SYNC_VIEWS else "WSGI",
        "timestamp": time.time(),
    }
    return render(request, "catalog/render.html", context)


async def catalog_render_async(request):
    """Asynchronous template rendering: gathers data asynchronously and renders concurrently."""
    limit = int(request.GET.get("limit", 25))
    qs = (
        Product.objects.filter(is_active=True)
        .select_related("category")
        .order_by("-created_at")[:limit]
    )
    products = [p async for p in qs]

    cat_qs = Category.objects.annotate(prod_count=Count("products"))
    categories = [c async for c in cat_qs]

    total_stock = sum(p.stock for p in products)
    avg_price = (sum(p.price for p in products) / len(products)) if products else Decimal(0)
    top_rated = sorted(products, key=lambda p: p.rating, reverse=True)[:5]

    mode_label = "ASGI-Async" if getattr(settings, "IS_ASYNC_BACKEND", False) else "ASGI"
    context = {
        "title": "Enterprise Product Showcase",
        "products": products,
        "categories": categories,
        "stats": {
            "displayed_count": len(products),
            "total_stock": total_stock,
            "avg_price": round(float(avg_price), 2),
            "top_rated": top_rated,
        },
        "mode": mode_label,
        "timestamp": time.time(),
    }

    # Offload CPU-heavy DTL rendering to threadpool concurrently without blocking the main event loop
    html_content = await render_template_async("catalog/render.html", context)
    return HttpResponse(html_content, content_type="text/html")


# ---------------------------------------------------------------------------
# 3. JSON API Serialization & Deserialization (/api/items)
# ---------------------------------------------------------------------------

def _serialize_product(p):
    return {
        "id": p.id,
        "sku": p.sku,
        "name": p.name,
        "price": float(p.price),
        "stock": p.stock,
        "rating": p.rating,
        "category": {
            "id": p.category.id,
            "name": p.category.name,
            "slug": p.category.slug,
        },
        "tags": p.tags,
        "specifications": p.specifications,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


@csrf_exempt
def items_api_sync(request):
    if request.method == "GET":
        limit = min(int(request.GET.get("limit", 25)), 100)
        offset = int(request.GET.get("offset", 0))

        qs = Product.objects.filter(is_active=True).select_related("category")
        total = qs.count()
        products = list(qs[offset : offset + limit])

        return JsonResponse({
            "total": total,
            "offset": offset,
            "limit": limit,
            "items": [_serialize_product(p) for p in products],
        })

    elif request.method == "POST":
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except Exception as e:
            return JsonResponse({"error": f"Invalid JSON payload: {str(e)}"}, status=400)

        category_id = payload.get("category_id")
        if not category_id:
            category = Category.objects.first()
        else:
            category = Category.objects.filter(id=category_id).first()
            if not category:
                return JsonResponse({"error": "Category not found"}, status=404)

        sku = payload.get("sku") or f"SKU-{int(time.time() * 1000)}-{os.urandom(2).hex()}"
        product = Product.objects.create(
            category=category,
            sku=sku,
            name=payload.get("name", "Benchmark Sample Product"),
            description=payload.get("description", "Synthetic product description generated during load test."),
            price=Decimal(str(payload.get("price", "99.95"))),
            stock=int(payload.get("stock", 50)),
            rating=float(payload.get("rating", 4.5)),
            tags=payload.get("tags", ["synthetic", "bench"]),
            specifications=payload.get("specifications", {"weight": "1.2kg", "origin": "EU"}),
        )
        return JsonResponse(_serialize_product(product), status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
async def items_api_async(request):
    if request.method == "GET":
        limit = min(int(request.GET.get("limit", 25)), 100)
        offset = int(request.GET.get("offset", 0))

        qs = Product.objects.filter(is_active=True).select_related("category")
        total = await qs.acount()
        items = []
        async for p in qs[offset : offset + limit]:
            items.append(_serialize_product(p))

        return JsonResponse({
            "total": total,
            "offset": offset,
            "limit": limit,
            "items": items,
        })

    elif request.method == "POST":
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except Exception as e:
            return JsonResponse({"error": f"Invalid JSON payload: {str(e)}"}, status=400)

        category_id = payload.get("category_id")
        if not category_id:
            category = await Category.objects.afirst()
        else:
            category = await Category.objects.filter(id=category_id).afirst()
            if not category:
                return JsonResponse({"error": "Category not found"}, status=404)

        sku = payload.get("sku") or f"SKU-{int(time.time() * 1000)}-{os.urandom(2).hex()}"
        product = await Product.objects.acreate(
            category=category,
            sku=sku,
            name=payload.get("name", "Benchmark Sample Product"),
            description=payload.get("description", "Synthetic product description generated during load test."),
            price=Decimal(str(payload.get("price", "99.95"))),
            stock=int(payload.get("stock", 50)),
            rating=float(payload.get("rating", 4.5)),
            tags=payload.get("tags", ["synthetic", "bench"]),
            specifications=payload.get("specifications", {"weight": "1.2kg", "origin": "EU"}),
        )
        return JsonResponse(_serialize_product(product), status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)


# ---------------------------------------------------------------------------
# 4. Third-Party Unreliable API Simulation (/external/fetch)
# ---------------------------------------------------------------------------

def external_fetch_sync(request):
    """Synchronous call to fake-api using connection-pooled requests.Session."""
    min_ms = request.GET.get("min", "50")
    max_ms = request.GET.get("max", "200")
    url = f"{settings.FAKE_API_URL}/delay?min={min_ms}&max={max_ms}"

    session = get_sync_session()
    start_time = time.perf_counter()
    try:
        resp = session.get(url, timeout=15.0)
        resp_data = resp.json()
        status_code = resp.status_code
    except Exception as exc:
        resp_data = {"error": str(exc)}
        status_code = 502

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    return JsonResponse({
        "status": "success" if status_code == 200 else "failed",
        "external_response": resp_data,
        "roundtrip_ms": elapsed_ms,
        "concurrency_mode": "wsgi_sync_blocking",
    }, status=status_code)


async def external_fetch_async(request):
    """Asynchronous non-blocking call using shared connection-pooled httpx.AsyncClient."""
    min_ms = request.GET.get("min", "50")
    max_ms = request.GET.get("max", "200")
    url = f"{settings.FAKE_API_URL}/delay?min={min_ms}&max={max_ms}"

    client = get_async_client()
    start_time = time.perf_counter()
    try:
        resp = await client.get(url)
        resp_data = resp.json()
        status_code = resp.status_code
    except Exception as exc:
        resp_data = {"error": str(exc)}
        status_code = 502

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    return JsonResponse({
        "status": "success" if status_code == 200 else "failed",
        "external_response": resp_data,
        "roundtrip_ms": elapsed_ms,
        "concurrency_mode": "asgi_async_nonblocking",
    }, status=status_code)


# ---------------------------------------------------------------------------
# 5. Database Search & Aggregations (/catalog/search)
# ---------------------------------------------------------------------------

def catalog_search_sync(request):
    query = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "").strip()

    qs = Product.objects.filter(is_active=True).select_related("category")
    if query:
        qs = qs.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if category_slug:
        qs = qs.filter(category__slug=category_slug)

    aggregates = qs.aggregate(
        total_items=Count("id"),
        avg_price=Avg("price"),
        min_price=Min("price"),
        max_price=Max("price"),
        avg_rating=Avg("rating"),
    )

    results = list(qs[:20])

    return JsonResponse({
        "query": query,
        "category": category_slug,
        "aggregates": {
            "total_items": aggregates["total_items"],
            "avg_price": round(float(aggregates["avg_price"] or 0), 2),
            "min_price": float(aggregates["min_price"] or 0),
            "max_price": float(aggregates["max_price"] or 0),
            "avg_rating": round(float(aggregates["avg_rating"] or 0), 2),
        },
        "results": [_serialize_product(p) for p in results],
    })


async def catalog_search_async(request):
    query = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "").strip()

    qs = Product.objects.filter(is_active=True).select_related("category")
    if query:
        qs = qs.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if category_slug:
        qs = qs.filter(category__slug=category_slug)

    aggregates = await qs.aaggregate(
        total_items=Count("id"),
        avg_price=Avg("price"),
        min_price=Min("price"),
        max_price=Max("price"),
        avg_rating=Avg("rating"),
    )

    results = []
    async for p in qs[:20]:
        results.append(_serialize_product(p))

    return JsonResponse({
        "query": query,
        "category": category_slug,
        "aggregates": {
            "total_items": aggregates["total_items"],
            "avg_price": round(float(aggregates["avg_price"] or 0), 2),
            "min_price": float(aggregates["min_price"] or 0),
            "max_price": float(aggregates["max_price"] or 0),
            "avg_rating": round(float(aggregates["avg_rating"] or 0), 2),
        },
        "results": results,
    })


# ---------------------------------------------------------------------------
# Health & Diagnostic Probe
# ---------------------------------------------------------------------------

def health_check(request):
    return JsonResponse({
        "status": "ok",
        "wsgi_mode": IS_WSGI,
        "async_backend": getattr(settings, "IS_ASYNC_BACKEND", False),
        "timestamp": time.time(),
    })


# ---------------------------------------------------------------------------
# Mode-Aware Route Binding
# ---------------------------------------------------------------------------

if IS_WSGI or FORCE_SYNC_VIEWS:
    auth_login = auth_login_sync
    catalog_render = catalog_render_sync
    items_api = items_api_sync
    external_fetch = external_fetch_sync
    catalog_search = catalog_search_sync
else:
    auth_login = auth_login_async
    catalog_render = catalog_render_async
    items_api = items_api_async
    external_fetch = external_fetch_async
    catalog_search = catalog_search_async
