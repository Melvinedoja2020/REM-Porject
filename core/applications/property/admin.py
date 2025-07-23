from django.contrib import admin
from django.utils.html import format_html

from core.applications.property.models import Amenity
from core.applications.property.models import FavoriteProperty
from core.applications.property.models import Lead
from core.applications.property.models import Property
from core.applications.property.models import PropertyImage
from core.applications.property.models import PropertySubscription
from core.applications.property.models import PropertyType

# Register your models here.


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    inlines = [PropertyImageInline]
    list_display = ["title", "price", "location", "is_available"]
    search_fields = ["title", "location"]
    list_filter = ["is_available", "property_type"]
    ordering = ["-created_at"]
    filter_horizontal = ["amenities"]

    def cover_image_preview(self, obj):
        """
        Returns a preview of the cover image for the property.
        If no cover image is set, returns a placeholder.
        """
        if obj.cover:
            return format_html(
                '<img src="{}" width="100" />',
                obj.cover.image.url,
            )
        return "-"


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


@admin.register(PropertyType)
class PropertyTypeAdmin(admin.ModelAdmin):
    list_display = ["title"]
    search_fields = ["title"]
    ordering = ["-created_at"]


@admin.register(FavoriteProperty)
class FavoritePropertyAdmin(admin.ModelAdmin):
    list_display = ["user", "property"]
    search_fields = ["user__username", "property__title"]
    ordering = ["-created_at"]
    list_filter = ["user"]


@admin.register(PropertySubscription)
class PropertySubscriptionAdmin(admin.ModelAdmin):
    list_display = ["user", "location", "property_type"]
    search_fields = ["user__username", "location", "property_type"]
    ordering = ["-created_at"]
    list_filter = ["user", "property_type"]


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ["property_link", "user", "status"]
    search_fields = ["property_link", "user__username"]
    ordering = ["-created_at"]
    list_filter = ["status", "property_link"]
