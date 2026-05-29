from django.db.models.signals import post_save
from django.dispatch import receiver

from core.applications.users.models import AgentProfile
from core.helpers.enums import SubscriptionPlan


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
