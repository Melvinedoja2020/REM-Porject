from django.urls import path

from core.applications.property.views import CreatePropertySubscriptionView
from core.applications.property.views import FavoriteDeleteView
from core.applications.property.views import FavoriteLeadCreateView
from core.applications.property.views import FavoriteListView
from core.applications.property.views import LeadDetailView
from core.applications.property.views import LeadListView
from core.applications.property.views import LeadUpdateView
from core.applications.property.views import PropertyCreateView
from core.applications.property.views import PropertyDeleteView
from core.applications.property.views import PropertyListView
from core.applications.property.views import PropertyUpdateView
from core.applications.property.views import ViewingScheduleView

app_name = "property"

urlpatterns = [
    path("create/", PropertyCreateView.as_view(), name="property_create"),
    path("properties", PropertyListView.as_view(), name="property_list"),
    path(
        "edit/<uuid:pk>/update/",
        PropertyUpdateView.as_view(),
        name="property_update",
    ),
    path(
        "delete/<uuid:pk>/delete/",
        PropertyDeleteView.as_view(),
        name="property_delete",
    ),
    path("my-favorites/", FavoriteListView.as_view(), name="customers_favorite_list"),
    path(
        "favorite/delete/<uuid:pk>/",
        FavoriteDeleteView.as_view(),
        name="delete_favorite",
    ),
    path(
        "favorites/<uuid:pk>/lead/",
        FavoriteLeadCreateView.as_view(),
        name="favorite_lead_create",
    ),
    path(
        "subscribe/",
        CreatePropertySubscriptionView.as_view(),
        name="create-subscription",
    ),
    path("leads/", LeadListView.as_view(), name="lead_list"),
    # path("leads/create/", LeadCreateView.as_view(), name="lead_create"),
    path("leads/<str:pk>/", LeadDetailView.as_view(), name="lead_detail"),
    path("leads/<str:pk>/update/", LeadUpdateView.as_view(), name="lead_update"),
    path(
        "leads/<str:pk>/schedule/",
        ViewingScheduleView.as_view(),
        name="schedule_viewing",
    ),
]
