from core.applications.notifications.models import Announcement, Notification
from core.helper.enums import ICON_CLASSES, PropertyTypeChoices
from django.utils import timezone


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
            "icon_class": ICON_CLASSES.get(choice.value, "icon-apartment1")  # fallback
        }
        for choice in PropertyTypeChoices
    ],
    "property_listing_type_counts": {
        choice.value: PropertyTypeChoices.choices.count(choice)
        for choice in PropertyTypeChoices
    }
    }

    if request.user.is_authenticated:
        user = request.user
        context["favorite_property_ids"] = list(user.favorites.values_list("property_id", flat=True))
        context["user_has_favorites"] = user.favorites.exists()
        context["latest_notifications"] = Notification.objects.filter(user=user).order_by("-created_at")[:5]
        context["unmarked_notifications"] = Notification.objects.filter(user=user, is_read=False).count()

    return context


def announcements(request):
    now = timezone.now()
    active_announcements = Announcement.objects.filter(
        visible=True,
        start_date__lte=now,
        end_date__gte=now
    ).order_by("-priority", "-created_at")[:5]  # Limit to 5 most important
    
    return {
        "active_announcements": active_announcements,
        "has_announcements": active_announcements.exists()
    }