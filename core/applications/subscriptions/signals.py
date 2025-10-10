from core.applications.subscriptions.models import AgentSubscription
from core.applications.users.models import AgentProfile
from django.dispatch import receiver
from django.db.models.signals import post_save


@receiver(post_save, sender=AgentProfile)
def create_trial_for_new_agent(sender, instance, created, **kwargs):
    if created:
        # Create a trial only if there is no previous trial (defensive)
        if not instance.subscriptions.filter(is_trial=True).exists():
            sub = AgentSubscription.objects.create(
                agent=instance, plan="Basic", is_trial=True, is_active=True
            )
            instance.set_current_subscription(sub)
