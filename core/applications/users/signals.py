from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.core.mail import send_mail
from django.db.models.signals import post_migrate
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.applications.notifications.models import NotificationPreference
from core.applications.property.models import User
from core.applications.users.models import AgentProfile
from core.helpers.enums import SubscriptionPlan


@receiver(post_migrate)
def create_default_groups(sender, **kwargs):
    admin_group, created = Group.objects.get_or_create(name="Admin")
    agent_group, created = Group.objects.get_or_create(name="Agent")
    customer_group, created = Group.objects.get_or_create(name="Customer")

    # Assign permissions (Example: Vendor can add products)
    agent_permissions = Permission.objects.filter(
        codename__in=[
            "add_house",
            "change_house",
            "delete_house",
            "view_house",
        ],
    )
    customer_group.permissions.set(agent_permissions)


@receiver(post_save, sender=AgentProfile)
def notify_agent_approval(sender, instance, created, **kwargs):
    if not created and instance.verified:
        send_mail(
            subject="Agent Profile Approved",
            message="Congratulations! Your agent profile has been verified. You can now list properties.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instance.user.email],
        )


@receiver(post_save, sender=User)
def create_user_notification_pref(sender, instance, created, **kwargs):
    if created:
        NotificationPreference.objects.get_or_create(user=instance)

@receiver(post_save, sender=AgentProfile)
def assign_free_subscription(sender, instance, created, **kwargs):
    """
    Automatically assigns a FREE tier subscription when an AgentProfile
    is first created.

    - FREE tier never expires (end_date=None)
    - No trial — agents start on FREE and upgrade when ready
    - Skips if a subscription already exists (defensive guard)
    """
    if not created:
        return

    from core.applications.subscriptions.models import AgentSubscription

    # Defensive guard — never create duplicate subscriptions
    if instance.subscriptions.exists():
        return

    subscription = AgentSubscription.objects.create(
        agent=instance,
        plan=SubscriptionPlan.FREE,
        is_active=True,
        is_trial=False,
        amount_paid=0,
        end_date=None,  # FREE tier never expires
    )

    instance.set_current_subscription(subscription)
