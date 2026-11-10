from django.urls import path
from .views import ResearchAndDraftView

urlpatterns = [
    path("research-and-draft/", ResearchAndDraftView.as_view(), name="research-and-draft"),
]
