from rest_framework.routers import DefaultRouter
from .views import NicheConfigViewSet

router = DefaultRouter()
router.register("niches", NicheConfigViewSet, basename="niches")

urlpatterns = router.urls
