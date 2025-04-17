from django.urls import path

from core.applications.home.views import HomeView, RentPropertyDetailView, RentPropertyListView



app_name = "home"

urlpatterns = [
    path("", HomeView.as_view(), name="home"), 
    path("rents", RentPropertyListView.as_view(), name="property_rent_list"),
    path(
        "rent/property/<slug:slug>/", RentPropertyDetailView.as_view(), 
        name="rent_property_detail"
    ),
]
