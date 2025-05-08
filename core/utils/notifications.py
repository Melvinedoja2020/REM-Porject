from django.db.models import Q

from core.applications.notifications.models import Notification, NotificationPreference
from core.applications.property.models import PropertySubscription
from core.helper.enums import NotificationType
from core.utils.utils import (
    is_user_subscribed_for_property,
    send_notification_email,
    send_push_notification,
    create_notification,
)


def notify_new_property_listing(property_instance):
    """
    Notify users who are subscribed to the location or type of a new property.
    """
    subscriptions = PropertySubscription.objects.filter(
        Q(property_type=property_instance.property_type) | Q(property_type__isnull=True)
    )

    property_location = (property_instance.location or "").lower()

    for sub in subscriptions:
        sub_location = (sub.location or "").lower()
        if not sub_location or sub_location in property_location:
            create_notification(
                user=sub.user,
                notification_type=NotificationType.NEW_LISTING,
                title="New Property Listing",
                message=f"A new {property_instance.property_type} is available in {property_instance.location}.",
                property=property_instance,
                metadata={'property_id': property_instance.id}
            )


def notify_price_change(property_instance, old_price):
    """
    Notify favoriting users about a price change if they are subscribed.
    """
    for user in property_instance.favorited_by.all():
        if is_user_subscribed_for_property(user, property_instance):
            create_notification(
                user=user,
                notification_type=NotificationType.PRICE_CHANGE,
                title=f"Price Update: {property_instance.title}",
                message=f"Price changed from ${old_price} to ${property_instance.price}.",
                property=property_instance,
                metadata={'old_price': old_price}
            )
