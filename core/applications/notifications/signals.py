# notifications/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from core.applications.notifications.utils import create_notification
from core.applications.property.models import Property
from messaging.models import Message


User = get_user_model()

@receiver(post_save, sender=Message)
def notify_new_message(sender, instance, created, **kwargs):
    if created:
        create_notification(
            user=instance.receiver,
            notification_type='message',
            title=f"New message from {instance.sender.get_full_name()}",
            message=instance.message,
            message=instance
        )

@receiver(post_save, sender=Property)
def notify_price_change(sender, instance, created, **kwargs):
    if not created and instance.tracker.has_changed('price'):
        old_price = instance.tracker.previous('price')
        # Notify users who favorited this property
        for user in instance.favorited_by.all():
            create_notification(
                user=user,
                notification_type='price_change',
                title=f"Price changed for {instance.title}",
                message=f"Price changed from ${old_price} to ${instance.price}",
                property=instance,
                metadata={'old_price': old_price}
            )