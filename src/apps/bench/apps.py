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
        except (ImportError, AttributeError):
            pass
