from django.contrib import admin

from core.applications.property.models import Property, PropertyImage, Amenity

# Register your models here.

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ["title", "price", "location", "is_available"]
    search_fields = ["title", "location"]
    list_filter = ["is_available", "property_type"]
    ordering = ["-created_at"]
    filter_horizontal = ["amenities"]


@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ["property", "image"]
    search_fields = ["property__title"]
    ordering = ["-created_at"]


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]
    ordering = ["-created_at"]

    