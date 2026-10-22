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


app = Starlette(
    debug=False,
    routes=[
        Route("/health", health, methods=["GET"]),
        Route("/delay", delay_endpoint, methods=["GET"]),
    ],
)
