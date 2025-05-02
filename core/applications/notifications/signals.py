from django.db.models.signals import post_save
from django.dispatch import receiver
from core.applications.notifications.models import Message
from core.applications.notifications.utils import create_notification
from core.applications.property.models import Property
from core.helper.enums import NotificationType
from subscriptions.models import PropertySubscription
from django.db import models

# Helper function to check if the user should receive a subscription-based notification
def is_user_subscribed_for_property(user, property_obj):
    return PropertySubscription.objects.filter(
        user=user,
        location__icontains=property_obj.location,
    ).filter(
        models.Q(property_type=property_obj.property_type) | models.Q(property_type__isnull=True)
    ).exists()

# Signal handler for message notifications
@receiver(post_save, sender=Message)
def notify_new_message(sender, instance, created, **kwargs):
    if created:
        create_notification(
            user=instance.receiver,
            notification_type=NotificationType.MESSAGE,
            title=f"New message from {instance.sender.get_full_name()}",
            message=instance.message,
            metadata={'message_id': instance.id}
        )

# Signal handler for property-related notifications (New listings and price changes)
@receiver(post_save, sender=Property)
def notify_on_property_change(sender, instance, created, **kwargs):
    # New Property Listing
    if created and instance.is_available:
        subs = PropertySubscription.objects.filter(
            models.Q(location__icontains=instance.location) | models.Q(location__isnull=True),
            models.Q(property_type=instance.property_type) | models.Q(property_type__isnull=True)
        )
        for sub in subs:
            create_notification(
                user=sub.user,
                notification_type=NotificationType.NEW_LISTING,
                title="New Property Listing",
                message=f"A new {instance.property_type} is available in {instance.location}.",
                property=instance,
                metadata={'property_id': instance.id}
            )

    # Price Change Notification for Favorited Properties
    elif instance.tracker.has_changed('price') and instance.is_available:
        old_price = instance.tracker.previous('price')
        for user in instance.favorited_by.all():
            if is_user_subscribed_for_property(user, instance):
                create_notification(
                    user=user,
                    notification_type=NotificationType.PRICE_CHANGE,
                    title=f"Price Update: {instance.title}",
                    message=f"Price changed from ${old_price} to ${instance.price}.",
                    property=instance,
                    metadata={'old_price': old_price}
                )
