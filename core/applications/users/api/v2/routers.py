from django.conf import settings
from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from core.applications.users.api.v2.views import AdminAgentViewSet
from core.applications.users.api.v2.views import AdminPropertyViewSet

PREFIX = "users-admin"

API_VERSION = settings.API_VERSION

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("admin/agents", AdminAgentViewSet, basename="admin-agents")
router.register("admin/properties", AdminPropertyViewSet, basename="admin-properties")

app_name = f"{PREFIX}"
urlpatterns = router.urls
