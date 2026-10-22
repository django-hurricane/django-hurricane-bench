from django.urls import path
from apps.bench import views

app_name = "bench"

urlpatterns = [
    path("api/auth/login", views.auth_login, name="auth_login"),
    path("api/auth/me", views.auth_me, name="auth_me"),
    path("catalog/render", views.catalog_render, name="catalog_render"),
    path("api/items", views.items_api, name="items_api"),
    path("external/fetch", views.external_fetch, name="external_fetch"),
    path("catalog/search", views.catalog_search, name="catalog_search"),
    path("api/gateway/aggregate", views.gateway_aggregate, name="gateway_aggregate"),
    path("health", views.health_check, name="health_check"),
]
