from django.apps import AppConfig

class BenchConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.bench"
    verbose_name = "Benchmark App"
