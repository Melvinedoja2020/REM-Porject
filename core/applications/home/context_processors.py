from core.applications.notifications.models import Notification


def user_context(request):
    """
    Unified context processor to provide:
    - Favorite property IDs
    - Whether user has any favorites
    - Latest notifications (limit 5)
    - Unread notifications count
    """
    context = {
        "favorite_property_ids": [],
        "user_has_favorites": False,
        "unmarked_notifications": 0,
        "latest_notifications": [],
    }

    if request.user.is_authenticated:
        user = request.user
        context["favorite_property_ids"] = list(user.favorites.values_list("property_id", flat=True))
        context["user_has_favorites"] = user.favorites.exists()
        context["latest_notifications"] = Notification.objects.filter(user=user).order_by("-created_at")[:5]
        context["unmarked_notifications"] = Notification.objects.filter(user=user, is_read=False).count()

    return context