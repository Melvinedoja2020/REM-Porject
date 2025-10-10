# subscriptions/services.py
from django.core.exceptions import ValidationError

from core.applications.subscriptions.features import FEATURE_LIMITS
from core.helper.enums import SubscriptionPlan


class SubscriptionService:
    """Service class for subscription-related operations."""

    @staticmethod
    def get_agent_plan(agent):
        """Return agent's current plan, defaults to FREE."""
        subscription = getattr(agent, "current_subscription", None)
        if subscription and subscription.is_valid():
            return subscription.plan
        return SubscriptionPlan.FREE

    @staticmethod
    def check_feature_limit(agent, feature_name: str, current_count: int):
        """
        Ensure agent has not exceeded the feature limit for their plan.
        """
        plan = SubscriptionService.get_agent_plan(agent)
        limit = FEATURE_LIMITS.get(plan, {}).get(feature_name)

        if limit is not None and current_count >= limit:
            raise ValidationError(
                f"You have reached the {feature_name.replace('_', ' ')} "
                f"limit ({limit}) for the {plan} plan. Please upgrade."
            )
