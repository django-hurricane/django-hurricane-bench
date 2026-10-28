from django.apps import AppConfig


class BenchConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.bench"
    verbose_name = "Benchmark App"

    def ready(self):
        try:
            import os
            import hurricane.management.commands.serve as h_serve
            from granian import Granian as OriginalGranian
            from granian.constants import Interfaces

            class SafeGranian(OriginalGranian):
                def __init__(self, *args, **kwargs):
                    if kwargs.get("interface") != Interfaces.WSGI:
                        # Granian strictly forbids blocking_threads > 1 on ASGI/RSGI
                        if kwargs.get("blocking_threads", 1) > 1:
                            # Re-route auto concurrency to Tokio event loop runtime_threads
                            kwargs["runtime_threads"] = min(16, max(1, os.cpu_count() or 1))
                            kwargs["blocking_threads"] = 1
                    super().__init__(*args, **kwargs)

            h_serve.Granian = SafeGranian

            from hurricane.server.gateway import HurricaneASGIGateway

            async def _try_handle_rate_limit(self, scope, send, start_time):
                if not getattr(self, "rate_limiter", None):
                    return False
                client = scope.get("client")
                client_ip = client[0] if client else "127.0.0.1"
                for name, value in scope.get("headers", []):
                    if name == b"x-forwarded-for":
                        client_ip = value.decode("latin1").split(",")[0].strip()
                        break
                    elif name == b"x-real-ip":
                        client_ip = value.decode("latin1").strip()
                        break
                if hasattr(self.rate_limiter, "limiter") and not self.rate_limiter.limiter.allow(client_ip):
                    _, _, body = self.rate_limiter.get_response()
                    await self._send_response(scope, send, 429, body, start_time, is_probe=False)
                    return True
                return False

            if not hasattr(HurricaneASGIGateway, "_try_handle_rate_limit"):
                HurricaneASGIGateway._try_handle_rate_limit = _try_handle_rate_limit
                orig_asgi_call = HurricaneASGIGateway.__call__

                async def patched_asgi_call(self, scope, receive, send):
                    if scope.get("type") == "http":
                        import time
                        start_time = time.perf_counter()
                        path = scope.get("path", "")
                        if await self._try_handle_fast_404(scope, send, path, start_time):
                            return
                        if await self._try_handle_rate_limit(scope, send, start_time):
                            return
                    return await orig_asgi_call(self, scope, receive, send)

                HurricaneASGIGateway.__call__ = patched_asgi_call
        except (ImportError, AttributeError):
            pass
