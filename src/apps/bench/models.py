from django.db import models

try:
    from django_async_backend.db.models.base import AsyncModelMixin
except ImportError:
    class AsyncModelMixin:
        pass


class Category(AsyncModelMixin, models.Model):
    name = models.CharField(max_length=100, db_index=True)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(AsyncModelMixin, models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    sku = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=200, db_index=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, db_index=True)
    stock = models.IntegerField(default=0)
    rating = models.FloatField(default=0.0)
    tags = models.JSONField(default=list)
    specifications = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_active", "price"]),
            models.Index(fields=["category", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.sku})"
