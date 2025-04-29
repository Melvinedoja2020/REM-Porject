from django.urls import path

from core.applications.property.views import (
    FavoriteDeleteView, PropertyCreateView, PropertyListView, PropertyUpdateView, 
    PropertyDeleteView, FavoriteListView
)

app_name = "property"

urlpatterns = [
    path("create/", PropertyCreateView.as_view(), name="property_create"),
    path("properties", PropertyListView.as_view(), name="property_list"),
    path("edit/<uuid:pk>/update/", PropertyUpdateView.as_view(), name="property_update"),
    path("delete/<uuid:pk>/delete/", PropertyDeleteView.as_view(), name="property_delete"),
    path("my-favorites/", FavoriteListView.as_view(), name="customers_favorite_list"),
    path("favorite/delete/<uuid:pk>/", FavoriteDeleteView.as_view(), name="delete_favorite"),

]
