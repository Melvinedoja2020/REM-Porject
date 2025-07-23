from django.db.models.signals import post_save
from django.dispatch import receiver

from core.applications.property.models import FavoriteProperty
from core.utils.utils import send_favorite_notifications


@receiver(post_save, sender=FavoriteProperty)
def send_favorite_notification(sender, instance, created, **kwargs):
    if created:  # Only notify when a new favorite is created
        agent = instance.property.agent
        user = instance.user  # This should be a User object

        # Log user to verify it's the correct object
        print(f"User object: {user}, User email: {user.email}")

        user_email = user.email  # This will work only if user is a User object
        send_favorite_notifications(agent, user_email, instance.property)


# @receiver(post_save, sender=Message)
# def notify_new_message(sender, instance, created, **kwargs):
#     """
#     Notify user when they receive a new message
#     """
#     print("am here now<<<<<<<<<<<<<<<<<<>>>>>>>>>>>>")
#     if created:
#         create_notification(
#             user=instance.receiver,
#             notification_type=NotificationType.MESSAGE,
#             title=f"New message from {instance.sender.name}",
#             message=instance.message,
#             metadata={'message_id': instance.id}
#         )


# @receiver(post_save, sender=Property)
# def notify_on_property_change(sender, instance, created, **kwargs):
#     print("i got here <<<<<<<<<<<<<<<<<<<<>>>>>>>>>>>>>")
#     """
#     Notify subscribed users on:
#     1. New property listing
#     2. Price change on a favorited property
#     """
#     # 1. New listing notification
#     if created and instance.is_available:
#         print(f"Signal hit: New property created: {instance} <<<<<<<<>>>>>>>>>>")
#         subscriptions = PropertySubscription.objects.filter(
#             models.Q(location__icontains=instance.location) | models.Q(location__isnull=True),
#             models.Q(property_type=instance.property_type) | models.Q(property_type__isnull=True)
#         )
#         for sub in subscriptions:
#             create_notification(
#                 user=sub.user,
#                 notification_type=NotificationType.NEW_LISTING,
#                 title="New Property Listing",
#                 message=f"A new {instance.property_type} is available in {instance.location}.",
#                 property=instance,
#                 metadata={'property_id': instance.id}
#             )

#     # 2. Price change notification
#     elif instance.tracker.has_changed('price') and instance.is_available:
#         old_price = instance.tracker.previous('price')
#         for user in instance.favorited_by.all():
#             if is_user_subscribed_for_property(user, instance):
#                 create_notification(
#                     user=user,
#                     notification_type=NotificationType.PRICE_CHANGE,
#                     title=f"Price Update: {instance.title}",
#                     message=f"Price changed from ${old_price} to ${instance.price}.",
#                     property=instance,
#                     metadata={'old_price': old_price}
#                 )
