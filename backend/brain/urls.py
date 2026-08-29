from __future__ import annotations

from rest_framework.routers import DefaultRouter

from .views import CompanyProfileViewSet, ProductViewSet, ServiceViewSet

router = DefaultRouter()
router.register("company", CompanyProfileViewSet, basename="company")
router.register("services", ServiceViewSet, basename="services")
router.register("products", ProductViewSet, basename="products")

urlpatterns = router.urls