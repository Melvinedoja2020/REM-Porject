

from core.applications.notifications.models import Notification, NotificationPreference
from core.applications.notifications.utils import send_notification_email
from core.helper.enums import NotificationType


def create_notification(user, notification_type, title, message, property=None, link=None, metadata=None):
    """
    Creates a notification for a user, respecting their preferences.
    If email_notifications = True, an email is sent as well.
    """
    prefs, _ = NotificationPreference.objects.get_or_create(user=user)

    # Check if the user has opted for this type of notification
    should_notify = {
        NotificationType.MESSAGE: prefs.new_message,
        NotificationType.PRICE_CHANGE: prefs.price_change,
        NotificationType.NEW_LISTING: prefs.new_listing,
        
        'viewing_update': prefs.viewing_update,
    }.get(notification_type, False)

    # If the user prefers no notification of this type, return early
    if not should_notify:
        return None

    # Create the notification
    notification = Notification.objects.create(
        user=user,
        title=title,
        notification_type=notification_type,
        message=message,
        property=property,
        link=link,
        extra_data=metadata or {},
    )

    # If email is enabled in preferences, send an email
    if prefs.email_enabled:
        send_notification_email(notification)

    return notification
