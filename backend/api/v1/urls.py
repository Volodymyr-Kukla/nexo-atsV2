from core.views import health
from django.urls import include, path

urlpatterns = [
    path("health/", health, name="health"),
    path("", include("users.urls")),
]
