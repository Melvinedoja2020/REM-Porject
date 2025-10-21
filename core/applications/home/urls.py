from django.urls import path

from core.applications.home.views import AgentDetailView, WhyChooseREMView
from core.applications.home.views import AgentListView
from core.applications.home.views import BuyPropertyListView
from core.applications.home.views import FavoriteCountAPI
from core.applications.home.views import HomeView
from core.applications.home.views import PropertyDetailView
from core.applications.home.views import PropertyGalleryView
from core.applications.home.views import PropertyListView
from core.applications.home.views import PropertyTypeListView
from core.applications.home.views import RentPropertyListView
from core.applications.home.views import ToggleFavoriteView
from core.applications.home.views import ContactUsView
from core.applications.home.views import AboutUsView

app_name = "home"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("about-us", AboutUsView.as_view(), name="about_us"),
    path("why-choose-rem/", WhyChooseREMView.as_view(), name="why_choose_rem"),
    path("contact", ContactUsView.as_view(), name="contact_us"),
    path("properties", PropertyListView.as_view(), name="property_lists"),
    path("rents", RentPropertyListView.as_view(), name="property_rent_list"),
    path("buys", BuyPropertyListView.as_view(), name="property_buy_list"),
    path(
        "rent/property/<slug:slug>/",
        PropertyDetailView.as_view(),
        name="rent_property_detail",
    ),
    path("agents", AgentListView.as_view(), name="agent_list"),
    path(
        "agent/<slug:id>/",
        AgentDetailView.as_view(),
        name="agent_detail",
    ),
    path("property/favorite/", ToggleFavoriteView.as_view(), name="toggle_favorite"),
    path(
        "api/user/favorites/count/",
        FavoriteCountAPI.as_view(),
        name="favorites_count_api",
    ),
    path(
        "property/<str:property_id>/gallery/",
        PropertyGalleryView.as_view(),
        name="property_gallery",
    ),
    path(
        "properties/type/<str:type>/",
        PropertyTypeListView.as_view(),
        name="property_type_list",
    ),
]
