from rest_framework.routers import DefaultRouter
from .views import DailyDigestViewSet

router = DefaultRouter()
router.register("digests", DailyDigestViewSet, basename="digests")

urlpatterns = router.urls
