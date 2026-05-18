from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from core.applications.property.api.views import HomePageView
from core.applications.property.api.views import PropertyViewSet

PREFIX = "property"

API_VERSION = settings.API_VERSION

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register(
    "property",
    PropertyViewSet,
    basename="property",
)
router.register(
    "home",
    HomePageView,
    basename="home",
)


app_name = f"{PREFIX}"
urlpatterns = router.urls
