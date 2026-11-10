from rest_framework.routers import DefaultRouter
from .views import EmailMessageViewSet

router = DefaultRouter()
router.register("messages", EmailMessageViewSet, basename="messages")

urlpatterns = router.urls
