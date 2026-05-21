from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound
from rest_framework.exceptions import PermissionDenied

from core.applications.property.models import Amenity
from core.applications.property.models import FavoriteProperty
from core.applications.property.models import Lead
from core.applications.property.models import Property
from core.applications.property.models import PropertySubscription
from core.applications.property.models import PropertyViewing
from core.helpers.enums import PropertyListingType
from core.helpers.enums import PropertyViewingChoices

User = get_user_model()



# _LISTING_TYPE_META: dict[str, dict[str, str]] = {
#     PropertyListingType.FOR_SALE:      {"label": "For Sale",   "icon": "home"},
#     PropertyListingType.RENT:      {"label": "For Rent",   "icon": "key"},
#     PropertyListingType.SHORT_LET: {"label": "Short Let",  "icon": "calendar"},
# }


_LISTING_TYPE_META: dict[str, dict[str, str]] = {
    PropertyListingType.FOR_SALE: {
        "label":       "For Sale",
        "icon":        "home",
        "description": "Browse properties available for sale across Africa.",
    },
    PropertyListingType.RENT: {
        "label":       "For Rent",
        "icon":        "key",
        "description": "Find short and long-term rental properties for you.",
    },
    PropertyListingType.SHORT_LET: {
        "label":       "Short Let",
        "icon":        "calendar",
        "description": "Discover flexible short-let accommodation near you.",
    },
}

_PRICE_RANGE_OPTIONS: dict[str, list[dict]] = {
    PropertyListingType.FOR_SALE: [
        {"label": "Any price",                    "price_min": None,        "price_max": None},
        {"label": "Under ₦10,000,000",             "price_min": None,        "price_max": 10_000_000},
        {"label": "₦10,000,000 – ₦30,000,000",    "price_min": 10_000_000,  "price_max": 30_000_000},
        {"label": "₦30,000,000 – ₦50,000,000",    "price_min": 30_000_000,  "price_max": 50_000_000},
        {"label": "₦50,000,000 – ₦100,000,000",   "price_min": 50_000_000,  "price_max": 100_000_000},
        {"label": "₦100,000,000 – ₦200,000,000",  "price_min": 100_000_000, "price_max": 200_000_000},
        {"label": "Above ₦200,000,000",            "price_min": 200_000_000, "price_max": None},
    ],
    PropertyListingType.RENT: [
        {"label": "Any price",              "price_min": None,        "price_max": None},
        {"label": "Under ₦100,000/month",   "price_min": None,        "price_max": 100_000},
        {"label": "Under ₦200,000/month",   "price_min": None,        "price_max": 200_000},
        {"label": "Under ₦500,000/month",   "price_min": None,        "price_max": 500_000},
        {"label": "Under ₦1,000,000/month", "price_min": None,        "price_max": 1_000_000},
        {"label": "Above ₦1,000,000/month", "price_min": 1_000_000,   "price_max": None},
    ],
    PropertyListingType.SHORT_LET: [
        {"label": "Any price",            "price_min": None,      "price_max": None},
        {"label": "Under ₦50,000/night",  "price_min": None,      "price_max": 50_000},
        {"label": "Under ₦100,000/night", "price_min": None,      "price_max": 100_000},
        {"label": "Under ₦200,000/night", "price_min": None,      "price_max": 200_000},
        {"label": "Under ₦500,000/night", "price_min": None,      "price_max": 500_000},
        {"label": "Above ₦500,000/night", "price_min": 500_000,   "price_max": None},
    ],
}



def get_home_page_data(*, user=None) -> dict[str, Any]:
    """
    Returns a dict of data for the home page.
    The featured properties queryset is limited to 6 for performance
    and to match the home page design.
    Categories are annotated with counts of visible properties in each listing type
    for the category filter cards on the home page.
    The search_config dict provides the frontend with the necessary data to
    render the search form dropdowns without hard-coding listing types or price bands.

    """
    featured = list(
        Property.objects
        .visible()
        .available()
        .featured_active()
        .with_card_relations()
        .with_featured_annotation()
        .with_favorite_annotation(user=user)
        [:6]
    )

    raw_counts: dict[str, int] = Property.objects.category_counts()

    categories = [
        {
            "listing_type": listing_type,
            "label":        meta["label"],
            "icon":         meta["icon"],
            "description":  meta["description"],   # ← was missing
            "count":        raw_counts.get(listing_type, 0),
        }
        for listing_type, meta in _LISTING_TYPE_META.items()
    ]

    search_config = {
        "listing_types": [
            {"value": lt, "label": meta["label"]}
            for lt, meta in _LISTING_TYPE_META.items()
        ],
        "price_ranges": _PRICE_RANGE_OPTIONS,
    }

    return {
        "featured_properties": featured,
        "categories":          categories,
        "search_config":       search_config,
    }

def get_property_list(
    *,
    user=None,
    listing_type: str | None = None,
    property_type: str | None = None,
    location: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    min_bedrooms: int | None = None,
    max_bedrooms: int | None = None,
    min_bathrooms: int | None = None,
    amenity_ids: list | None = None,
    is_available: bool | None = None,
    search: str | None = None,
    ordering: str = "-created_at",
):
    """
    Returns an unevaluated QuerySet for the property listing page.

    All filter parameters are optional — omitting them returns the full
    visible set.  The view paginates before evaluation so the database
    only fetches the current page of rows.

    ``ordering`` is validated against a whitelist inside
    ``PropertyQuerySet.safe_order()`` — arbitrary field names from
    query params cannot leak through.
    """
    qs = (
        Property.objects
        .visible()
        .with_card_relations()
        .with_favorite_annotation(user=user)
    )

    if listing_type:
        qs = qs.by_listing_type(listing_type)
    if property_type:
        qs = qs.by_property_type(property_type)
    if location:
        qs = qs.by_location(location)
    if min_price is not None or max_price is not None:
        qs = qs.by_price_range(min_price=min_price, max_price=max_price)
    if min_bedrooms is not None or max_bedrooms is not None:
        qs = qs.by_bedrooms(min_bedrooms=min_bedrooms, max_bedrooms=max_bedrooms)
    if min_bathrooms is not None:
        qs = qs.by_bathrooms(min_bathrooms=min_bathrooms)
    if amenity_ids:
        qs = qs.by_amenities(amenity_ids)
    if is_available is not None:
        qs = qs.filter(is_available=is_available)
    if search:
        qs = qs.search(search)

    return qs.safe_order(ordering)



def get_property_detail(
    *, slug: str, user=None
) -> tuple[Property, list[Property]]:
    """
    Returns ``(property, similar_properties)``.

    Similar properties share the same listing type and property type,
    capped at 4.  They are fetched in a second evaluated query (list)
    so the main detail query is not complicated by slicing constraints.

    Raises ``NotFound`` when no visible property matches the slug.
    """
    try:
        prop = (
            Property.objects
            .visible()
            .with_detail_relations()
            .with_favorite_annotation(user=user)
            .get(slug=slug)
        )
    except Property.DoesNotExist:
        raise NotFound("Property not found.")

    similar = list(
        Property.objects
        .with_card_relations()
        .with_favorite_annotation(user=user)
        .similar_to(prop, limit=4)
    )

    return prop, similar



def create_property(*, agent, validated_data: dict) -> Property:
    """
    Creates a new property listing on behalf of an agent.

    Amenities are popped from ``validated_data`` and set via the M2M
    relation after the instance is saved.  ``Property.save()`` enforces
    plan-based listing limits and generates the slug — both via
    ``full_clean()`` which is called before commit.
    """
    amenities = validated_data.pop("amenities", [])
    with transaction.atomic():
        prop = Property(agent=agent, **validated_data)
        prop.full_clean()
        prop.save()
        if amenities:
            prop.amenities.set(amenities)
    return prop


def update_property(*, instance: Property, agent, validated_data: dict) -> Property:
    """
    Updates an existing property listing.
    Only the owning agent may update — enforced here as a service-layer
    guard in addition to the view-level object permission.
    """
    if str(instance.agent_id) != str(agent.pk):
        raise PermissionDenied("You do not own this property.")

    amenities = validated_data.pop("amenities", None)
    with transaction.atomic():
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.full_clean()
        instance.save()
        if amenities is not None:
            instance.amenities.set(amenities)
    return instance


def delete_property(*, instance: Property, agent) -> None:
    """
    Deletes a property listing.
    Only the owning agent may delete.
    """
    if str(instance.agent_id) != str(agent.pk):
        raise PermissionDenied("You do not own this property.")
    instance.delete()


def get_agent_properties(*, agent, user=None):
    """
    All listings owned by a given agent, annotated with lead_count and
    viewing_count for the agent dashboard table.
    Returns an unevaluated QuerySet.
    """
    return (
        Property.objects
        .visible()
        .for_agent(agent)
        .with_card_relations()
        .with_favorite_annotation(user=user)
        .with_listing_counts()
    )


# ---------------------------------------------------------------------------
# Favorites
# ---------------------------------------------------------------------------


def toggle_favorite(*, user, property_id) -> dict[str, Any]:
    """
    Atomically toggles a FavoriteProperty record.
    Idempotent — safe to call multiple times from the client.

    Returns a plain dict ready for ``FavoriteToggleSerializer``:
      { "property_id": ..., "is_favorited": bool, "message": str }
    """
    try:
        prop = Property.objects.get(pk=property_id, visible=True)
    except Property.DoesNotExist:
        raise NotFound("Property not found.")

    obj, created = FavoriteProperty.objects.get_or_create(
        user=user,
        property=prop,
    )
    if not created:
        obj.delete()
        return {
            "property_id": property_id,
            "is_favorited": False,
            "message": "Removed from favorites.",
        }
    return {
        "property_id": property_id,
        "is_favorited": True,
        "message": "Added to favorites.",
    }


def get_user_favorites(*, user):
    """
    Returns the authenticated user's favorited properties with all card
    fields pre-fetched.  Unevaluated — the view paginates.
    """
    return FavoriteProperty.objects.for_user(user).with_property_card()


# ---------------------------------------------------------------------------
# Property subscriptions (new-listing alerts)
# ---------------------------------------------------------------------------


def get_user_subscriptions(*, user):
    """Returns the user's alert subscriptions. Unevaluated."""
    return PropertySubscription.objects.for_user(user).order_by("-created_at")


def create_subscription(*, user, validated_data: dict) -> PropertySubscription:
    """Creates a new-listing alert subscription for the authenticated user."""
    return PropertySubscription.objects.create(user=user, **validated_data)


def delete_subscription(*, user, subscription_id) -> None:
    """
    Deletes the user's subscription.
    Raises ``NotFound`` when the record doesn't exist or belongs to
    a different user.
    """
    deleted, _ = PropertySubscription.objects.filter(
        user=user,
        pk=subscription_id,
    ).delete()
    if not deleted:
        raise NotFound("Subscription not found.")


# ---------------------------------------------------------------------------
# Leads
# ---------------------------------------------------------------------------


def create_lead(*, user, property_id, message: str = "") -> Lead:
    """
    Creates (or retrieves) a Lead when a user taps "Contact Agent".

    Idempotent — one Lead per (user, property) pair enforced by
    ``unique_together``.  Re-submissions update the message on the
    existing lead so the agent always sees the latest enquiry text.

    The agent FK is resolved from the property record — never supplied
    by the client.
    """
    try:
        prop = (
            Property.objects
            .select_related("agent")
            .get(pk=property_id, visible=True, is_available=True)
        )
    except Property.DoesNotExist:
        raise NotFound("Property not found or no longer available.")

    lead, created = Lead.objects.get_or_create(
        user=user,
        property_link=prop,
        defaults={"agent": prop.agent, "message": message},
    )

    if not created and message:
        Lead.objects.filter(pk=lead.pk).update(message=message)
        lead.message = message

    return lead


def get_lead(*, user, lead_id) -> Lead:
    """
    Fetches a single lead with full relations loaded.
    Raises ``NotFound`` when the lead doesn't exist or doesn't belong
    to the requesting user.
    """
    try:
        return Lead.objects.with_relations().get(pk=lead_id, user=user)
    except Lead.DoesNotExist:
        raise NotFound("Lead not found.")


def get_user_leads(*, user):
    """
    All leads created by a user (their enquiry history) with full
    relations pre-fetched.  Unevaluated — the view paginates.
    """
    return Lead.objects.for_user(user).with_relations()


def get_agent_leads(*, agent, status: str | None = None):
    """
    All leads for an agent's listings, with upcoming viewings and
    viewing counts pre-fetched.  Supports optional status filtering
    for the CRM pipeline view.  Unevaluated — the view paginates.
    """
    qs = Lead.objects.for_agent(agent).with_relations().with_viewing_count()
    if status:
        qs = qs.by_status(status)
    return qs


def update_lead_status(*, agent, lead_id, status: str) -> Lead:
    """
    Advances a lead's pipeline status.  Only the property's agent may
    update.  ``full_clean()`` enforces model-level status transition
    rules (e.g. VIEWING_SCHEDULED requires at least one viewing).
    """
    try:
        lead = Lead.objects.select_related("property_link").get(
            pk=lead_id,
            agent=agent,
        )
    except Lead.DoesNotExist:
        raise NotFound("Lead not found.")

    lead.status = status
    lead.last_contact = timezone.now()
    lead.full_clean()
    lead.save(update_fields=["status", "last_contact", "updated_at"])
    return lead




def create_viewing(*, user, validated_data: dict) -> PropertyViewing:
    """
    Books a viewing from the "Schedule a Viewing" modal.

    ``validated_data`` is the deserialised output of
    ``ViewingCreateSerializer``:
      • ``property_id``   — UUID of the target property (already validated)
      • ``lead``          — Lead instance or None (resolved during validation)
      • ``scheduled_time``— timezone-aware datetime
      • ``notes``         — optional string

    Side effect: when a lead is linked, its status is promoted to
    VIEWING_SCHEDULED and last_contact is updated in the same transaction.
    """
    property_id = validated_data.pop("property_id")
    lead = validated_data.pop("lead", None)

    with transaction.atomic():
        viewing = PropertyViewing(
            user=user,
            property_id=property_id,
            lead=lead,
            **validated_data,
        )
        viewing.full_clean()
        viewing.save()

        if lead is not None:
            Lead.objects.filter(pk=lead.pk).update(
                status="VIEWING_SCHEDULED",
                last_contact=timezone.now(),
            )

    return viewing


def cancel_viewing(*, user, viewing_id, reason: str = "") -> PropertyViewing:
    """
    Soft-cancels a viewing by setting status to CANCELLED.

    Authorised actors
    -----------------
      • The user who booked the viewing.
      • The agent who owns the property.

    Permission is re-checked here as a service-layer guard even though
    ``ViewingPermission`` already handles it at the view layer.
    """
    try:
        viewing = (
            PropertyViewing.objects
            .select_related("property__agent")
            .get(pk=viewing_id)
        )
    except PropertyViewing.DoesNotExist:
        raise NotFound("Viewing not found.")

    is_booking_user = str(viewing.user_id) == str(user.pk)
    is_property_agent = (
        hasattr(user, "agent_profile")
        and str(viewing.property.agent_id) == str(user.agent_profile.pk)
    )

    if not (is_booking_user or is_property_agent):
        raise PermissionDenied("You do not have permission to cancel this viewing.")

    viewing.status = PropertyViewingChoices.CANCELLED
    viewing.cancellation_reason = reason
    viewing.save(update_fields=["status", "cancellation_reason", "updated_at"])
    return viewing


def get_user_viewings(*, user):
    """
    All viewings for a user with property card pre-fetched.
    Ordered by most recent scheduled time first.
    Unevaluated — the view paginates.
    """
    return (
        PropertyViewing.objects
        .for_user(user)
        .with_relations()
        .order_by("-scheduled_time")
    )


# ---------------------------------------------------------------------------
# Amenities
# ---------------------------------------------------------------------------


def get_all_amenities():
    """
    Returns all amenities alphabetically.
    Used to populate the amenity filter checkbox list on the listing page.
    """
    return Amenity.objects.alphabetical()
