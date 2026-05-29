from __future__ import annotations

import auto_prefetch
from django.db.models import BooleanField
from django.db.models import Count
from django.db.models import Exists
from django.db.models import OuterRef
from django.db.models import Prefetch
from django.db.models import Q
from django.db.models import Value
from django.db.models.functions import Now

from core.applications.property import models as property_models
from core.helpers.enums import PropertyViewingChoices


class PropertyImageQuerySet(auto_prefetch.QuerySet):
    """Used for image ordering and prefetch consistency."""

    def ordered(self) -> "PropertyImageQuerySet":
        return self.order_by("order", "created_at")


class AmenityQuerySet(auto_prefetch.QuerySet):

    def alphabetical(self) -> "AmenityQuerySet":
        return self.order_by("name")

    def for_property(self, property_pk) -> "AmenityQuerySet":
        return self.filter(properties__pk=property_pk)




class PropertyQuerySet(auto_prefetch.QuerySet):
    """
    Core Property queryset with composable filters, annotations, and prefetches.
    """

    # -------------------------
    # Base filters
    # -------------------------

    def visible(self) -> "PropertyQuerySet":
        return self.filter(visible=True)

    def available(self) -> "PropertyQuerySet":
        return self.filter(is_available=True)

    def featured_active(self):
        """Filter properties that have an active featured listing."""
        return self.filter(
            property_featured_listings__is_active=True,
            property_featured_listings__end_date__gte=Now(),
        ).distinct()

    def with_featured_annotation(self) -> "PropertyQuerySet":
        """
        Annotate each property with `is_featured_now` boolean
        based on active featured listings.
        """
        from core.applications.subscriptions.models import FeaturedListing
        subquery = FeaturedListing.objects.filter(
            property=OuterRef("pk"),
            is_active=True,
            end_date__gte=Now(),
        )
        return self.annotate(is_featured_now=Exists(subquery))

    # -------------------------
    # Prefetch bundles
    # -------------------------

    def with_card_relations(self) -> "PropertyQuerySet":
        """For property cards and listings - minimal related data for display."""
        return (
            self.select_related(
                "agent",
                "agent__user",
            )
            .prefetch_related(
                Prefetch(
                    "images",
                    queryset=property_models.PropertyImage.objects.order_by(
                        "order", "created_at"
                    ),
                ),
                Prefetch(
                    "amenities",
                    queryset=property_models.Amenity.objects.alphabetical(),
                ),
                "property_featured_listings",
            )
        )

    def with_detail_relations(self) -> "PropertyQuerySet":
        return self.with_card_relations()

    def with_lead_relations(self) -> "PropertyQuerySet":
        return self.prefetch_related("leads", "leads__user")

    # -------------------------
    # Annotations
    # -------------------------

    def with_favorite_annotation(self, user=None) -> "PropertyQuerySet":
        """Annotate each property with `is_favorited` boolean for the given user."""
        if user and user.is_authenticated:
            subquery = property_models.FavoriteProperty.objects.filter(
                user=user,
                property=OuterRef("pk"),
            )
            return self.annotate(is_favorited=Exists(subquery))

        return self.annotate(
            is_favorited=Value(False, output_field=BooleanField())
        )

    def with_featured_annotation(self) -> "PropertyQuerySet":
        """Annotate each property with `is_featured_now` boolean based on active featured listings."""
        subquery = property_models.FeaturedListing.objects.filter(
            property=OuterRef("pk"),
            is_active=True,
            end_date__gte=Now(),
        )
        return self.annotate(is_featured_now=Exists(subquery))

    def with_listing_counts(self) -> "PropertyQuerySet":
        return self.annotate(
            lead_count=Count("leads", distinct=True),
            viewing_count=Count("viewings", distinct=True),
        )

    # -------------------------
    # Filters
    # -------------------------

    def by_listing_type(self, listing_type: str) -> "PropertyQuerySet":
        return self.filter(property_listing=listing_type)

    def by_property_type(self, property_type: str) -> "PropertyQuerySet":
        return self.filter(property_type=property_type)

    def by_location(self, location: str) -> "PropertyQuerySet":
        return self.filter(location__icontains=location)

    def by_price_range(self, min_price=None, max_price=None) -> "PropertyQuerySet":
        """
        Filter properties within a price range. Both min_price and max_price are optional.
        """
        qs = self
        if min_price is not None:
            qs = qs.filter(price__gte=min_price)
        if max_price is not None:
            qs = qs.filter(price__lte=max_price)
        return qs

    def by_bedrooms(self, min_bedrooms=None, max_bedrooms=None) -> "PropertyQuerySet":
        """
        Filter properties by number of bedrooms. Both min_bedrooms and max_bedrooms are optional.
        """
        qs = self
        if min_bedrooms is not None:
            qs = qs.filter(bedrooms__gte=min_bedrooms)
        if max_bedrooms is not None:
            qs = qs.filter(bedrooms__lte=max_bedrooms)
        return qs

    def by_bathrooms(self, min_bathrooms=None) -> "PropertyQuerySet":
        """
        Filter properties by number of bathrooms. The min_bathrooms parameter is optional.
        """
        return self.filter(bathrooms__gte=min_bathrooms) if min_bathrooms else self

    def by_amenities(self, amenity_ids: list) -> "PropertyQuerySet":
        if not amenity_ids:
            return self
        return self.filter(amenities__id__in=amenity_ids).distinct()

    def search(self, term: str) -> "PropertyQuerySet":
        """
        Search properties by title, location, or description. Case-insensitive partial match.
        """

        if not term:
            return self
        return self.filter(
            Q(title__icontains=term)
            | Q(location__icontains=term)
            | Q(description__icontains=term)
        )

    def safe_order(self, ordering: str) -> "PropertyQuerySet":
        allowed = {
            "price", "-price",
            "created_at", "-created_at",
            "bedrooms", "-bedrooms",
            "sqft", "-sqft",
            "title", "-title",
        }
        if ordering not in allowed:
            return self
        return self.order_by(ordering)

    def similar_to(self, prop, limit: int = 4) -> "PropertyQuerySet":
        return (
            self.visible()
            .available()
            .filter(
                property_listing=prop.property_listing,
                property_type=prop.property_type,
            )
            .exclude(pk=prop.pk)[:limit]
        )

    def for_agent(self, agent) -> "PropertyQuerySet":
        return self.filter(agent=agent)

    def category_counts(self) -> dict[str, int]:
        qs = (
            self.visible()
            .available()
            .values("property_listing")
            .annotate(count=Count("id"))
        )
        return {row["property_listing"]: row["count"] for row in qs}

    def featured_first(self) -> "PropertyQuerySet":
        return (
            self.with_featured_annotation()
            .order_by("-is_featured_now", "-created_at")
        )


# ---------------------------------------------------------------------------
# LEADS
# ---------------------------------------------------------------------------

class LeadQuerySet(auto_prefetch.QuerySet):

    def with_relations(self) -> "LeadQuerySet":
        upcoming_qs = property_models.PropertyViewing.objects.filter(
            status__in=[
                PropertyViewingChoices.PENDING,
                PropertyViewingChoices.CONFIRMED,
            ],
            scheduled_time__gte=Now(),
        ).order_by("scheduled_time")

        return (
            self.select_related(
                "user",
                "property_link",
                "property_link__agent",
                "property_link__agent__user",
            )
            .prefetch_related(
                Prefetch(
                    "viewings",
                    queryset=upcoming_qs,
                    to_attr="upcoming_viewings_cache",
                ),
                Prefetch(
                    "property_link__images",
                    queryset=property_models.PropertyImage.objects.ordered(),
                ),
            )
        )

    def for_agent(self, agent):
        return self.filter(agent=agent)

    def for_user(self, user):
        return self.filter(user=user)

    def by_status(self, status: str):
        return self.filter(status=status)

    def with_viewing_count(self):
        return self.annotate(viewing_count=Count("viewings", distinct=True))


# ---------------------------------------------------------------------------
# VIEWINGS
# ---------------------------------------------------------------------------

class PropertyViewingQuerySet(auto_prefetch.QuerySet):

    def with_relations(self):
        return (
            self.select_related(
                "user",
                "property",
                "property__agent",
                "property__agent__user",
                "lead",
            )
            .prefetch_related(
                Prefetch(
                    "property__images",
                    queryset=property_models.PropertyImage.objects.ordered(),
                ),
            )
        )

    def upcoming(self):
        return self.filter(
            status__in=[
                PropertyViewingChoices.PENDING,
                PropertyViewingChoices.CONFIRMED,
            ],
            scheduled_time__gte=Now(),
        )

    def for_user(self, user):
        return self.filter(user=user)

    def for_property(self, property_pk):
        return self.filter(property_id=property_pk)

    def for_lead(self, lead_pk):
        return self.filter(lead_id=lead_pk)

    def pending(self):
        return self.filter(status=PropertyViewingChoices.PENDING)

    def confirmed(self):
        return self.filter(status=PropertyViewingChoices.CONFIRMED)

    def cancelled(self):
        return self.filter(status=PropertyViewingChoices.CANCELLED)


# ---------------------------------------------------------------------------
# FAVORITES
# ---------------------------------------------------------------------------

class FavoritePropertyQuerySet(auto_prefetch.QuerySet):

    def for_user(self, user):
        return self.filter(user=user)

    def with_property_card(self):
        return (
            self.select_related(
                "property",
                "property__agent",
                "property__agent__user",
            )
            .prefetch_related(
                Prefetch(
                    "property__images",
                    queryset=property_models.PropertyImage.objects.ordered(),
                ),
                Prefetch(
                    "property__amenities",
                    queryset=property_models.Amenity.objects.alphabetical(),
                ),
                "property__property_featured_listings",
            )
            .order_by("-created_at")
        )


# ---------------------------------------------------------------------------
# SUBSCRIPTIONS
# ---------------------------------------------------------------------------

class PropertySubscriptionQuerySet(auto_prefetch.QuerySet):

    def for_user(self, user):
        return self.filter(user=user)

    def matching(self, location: str | None, property_type: str | None):
        q = Q()

        if location:
            q &= Q(location__icontains=location) | Q(location__isnull=True)

        if property_type:
            q &= Q(property_type=property_type) | Q(property_type__isnull=True)

        return self.filter(q).select_related("user")
