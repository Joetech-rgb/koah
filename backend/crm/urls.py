from rest_framework.routers import DefaultRouter
from .views import TargetCompanyViewSet

router = DefaultRouter()
router.register("companies", TargetCompanyViewSet, basename="companies")

urlpatterns = router.urls
