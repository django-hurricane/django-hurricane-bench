import asyncio
import random
import time
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route


async def health(request):
    return JSONResponse({"status": "healthy"})


async def delay_endpoint(request):
    """
    Simulates an unreliable third-party API with randomized delay between min and max (in ms).
    Query parameters:
        min: minimum delay in milliseconds (default: 50)
        max: maximum delay in milliseconds (default: 200)
    """
    try:
        min_ms = float(request.query_params.get("min", 50))
        max_ms = float(request.query_params.get("max", 200))
    except (ValueError, TypeError):
        min_ms = 50.0
        max_ms = 200.0

    if min_ms < 0:
        min_ms = 0.0
    if max_ms < min_ms:
        max_ms = min_ms

    delay_ms = random.uniform(min_ms, max_ms)
    delay_sec = delay_ms / 1000.0

    await asyncio.sleep(delay_sec)

    return JSONResponse({
        "status": "success",
        "simulated_delay_ms": round(delay_ms, 2),
        "min_param_ms": min_ms,
        "max_param_ms": max_ms,
        "timestamp": time.time(),
    })


async def user_service(request):
    """Simulates a microservice returning user profile & loyalty tier."""
    user_id = request.query_params.get("id", "benchuser")
    delay_ms = random.uniform(20.0, 40.0)
    await asyncio.sleep(delay_ms / 1000.0)
    return JSONResponse({
        "service": "user-profile",
        "user_id": user_id,
        "tier": "enterprise_gold",
        "discount_percent": 15,
        "loyalty_points": 2450,
        "latency_ms": round(delay_ms, 2),
    })


async def inventory_service(request):
    """Simulates a warehouse inventory microservice."""
    sku = request.query_params.get("sku", "SKU-DEFAULT")
    delay_ms = random.uniform(25.0, 45.0)
    await asyncio.sleep(delay_ms / 1000.0)
    return JSONResponse({
        "service": "warehouse-inventory",
        "sku": sku,
        "in_stock": True,
        "warehouse_location": "eu-central-frankfurt",
        "available_units": 85,
        "latency_ms": round(delay_ms, 2),
    })


async def recommendations_service(request):
    """Simulates an AI recommendations engine microservice."""
    sku = request.query_params.get("sku", "SKU-DEFAULT")
    delay_ms = random.uniform(30.0, 50.0)
    await asyncio.sleep(delay_ms / 1000.0)
    return JSONResponse({
        "service": "ai-recommendations",
        "target_sku": sku,
        "recommended_skus": ["SKU-AUTO-101", "SKU-AUTO-204", "SKU-AUTO-309"],
        "confidence_score": 0.94,
        "latency_ms": round(delay_ms, 2),
    })


app = Starlette(
    debug=False,
    routes=[
        Route("/health", health, methods=["GET"]),
        Route("/delay", delay_endpoint, methods=["GET"]),
        Route("/services/user", user_service, methods=["GET"]),
        Route("/services/inventory", inventory_service, methods=["GET"]),
        Route("/services/recommendations", recommendations_service, methods=["GET"]),
    ],
)
