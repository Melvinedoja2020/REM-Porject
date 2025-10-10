from django.utils import timezone

from core.applications.notifications.models import Announcement
from core.applications.notifications.models import Notification
from core.applications.property.models import FavoriteProperty, Lead, Property, PropertyViewing
from core.helper.enums import ICON_CLASSES
from core.helper.enums import PropertyTypeChoices
from django.db.models import Count, Sum


def user_context(request):
    """
    Unified context processor to provide:
    - Favorite property IDs
    - Whether user has any favorites
    - Latest notifications (limit 5)
    - Unread notifications count
    - Property listing type counts
    - Property listing types
    - Property listing type choices
    """

    context = {
        "favorite_property_ids": [],
        "user_has_favorites": False,
        "unmarked_notifications": 0,
        "latest_notifications": [],
        "property_listing_types": [
            {
                "label": choice.label,
                "value": choice.value,
                "icon_class": ICON_CLASSES.get(
                    choice.value,
                    "icon-apartment1",
                ),  # fallback
            }
            for choice in PropertyTypeChoices
        ],
        "property_listing_type_counts": {
            choice.value: PropertyTypeChoices.choices.count(choice)
            for choice in PropertyTypeChoices
        },
    }

    if request.user.is_authenticated:
        user = request.user
        context["favorite_property_ids"] = list(
            user.favorites.values_list("property_id", flat=True),
        )
        context["user_has_favorites"] = user.favorites.exists()
        context["latest_notifications"] = Notification.objects.filter(
            user=user,
        ).order_by("-created_at")[:5]
        context["unmarked_notifications"] = Notification.objects.filter(
            user=user,
            is_read=False,
        ).count()

    return context


def announcements(request):
    """
    Context processor to provide active announcements.
    Returns announcements that are currently visible and within the active date range.
    """
    now = timezone.now()
    active_announcements = Announcement.objects.filter(
        visible=True,
        start_date__lte=now,
        end_date__gte=now,
    ).order_by("-priority", "-created_at")[:5]  # Limit to 5 most important

    return {
        "active_announcements": active_announcements,
        "has_announcements": active_announcements.exists(),
    }


def property_types(request):
    return {
        "property_types": PropertyTypeChoices.choices
    }


def agent_dashboard_context(request):
    """
    Context processor for agent dashboard metrics.
    Returns dynamic data related to the logged-in agent:
    - Total deals closed
    - Total commission earned (currently placeholder)
    - Active listings
    - Property views
    - Property overview list
    """

    if not request.user.is_authenticated or not hasattr(request.user, "agent_profile"):
        return {}

    agent = request.user.agent_profile

    # Total properties listed by agent
    total_properties = Property.objects.filter(agent=agent).count()

    # Active listings
    active_listings = Property.objects.filter(agent=agent, is_available=True).count()

    # Total property views
    total_views = PropertyViewing.objects.filter(property__agent=agent).count()

    # Total deals closed
    total_deals = Lead.objects.filter(
        property_link__agent=agent,
        status__in=["closed", "completed"]
    ).count()

    # Total commission earned (placeholder)
    total_commission = 0

    # Property overview (latest 5)
    property_overview = (
        Property.objects.filter(agent=agent)
        .order_by("-created_at")[:5]
    )

    return {
        "total_properties": total_properties,
        "active_listings": active_listings,
        "total_property_views": total_views,
        "total_deals_closed": total_deals,
        "total_commission_earned": total_commission,
        "property_overview": property_overview,
    }

def customer_dashboard_context(request):
    """Provides key dashboard metrics for logged-in customers."""
    context = {}

    if request.user.is_authenticated and hasattr(request.user, "is_customer"):
        user = request.user

        # Favorites count
        favorite_count = FavoriteProperty.objects.filter(user=user).count()

        # Viewings (total and upcoming)
        total_viewings = PropertyViewing.objects.filter(user=user).count()
        upcoming_viewings = PropertyViewing.objects.filter(
            user=user,
            scheduled_time__gte=timezone.now(),
            status__in=["PENDING", "CONFIRMED"],
        ).count()

        # Leads (interested properties)
        total_leads = Lead.objects.filter(user=user).count()

        # Active/confirmed leads (if you track status)
        active_leads = Lead.objects.filter(
            user=user,
            status__in=["NEW", "VIEWING_SCHEDULED", "NEGOTIATION"],
        ).count()

        # You can extend this with more analytics later
        context.update({
            "favorite_count": favorite_count,
            "total_viewings": total_viewings,
            "upcoming_viewings": upcoming_viewings,
            "total_leads": total_leads,
            "active_leads": active_leads,
        })

    return context
