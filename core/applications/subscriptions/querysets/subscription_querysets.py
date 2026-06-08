from __future__ import annotations

import auto_prefetch
from django.db.models import Count
from django.db.models import Exists
from django.db.models import OuterRef
from django.db.models import Prefetch
from django.db.models import Q
from django.db.models.functions import Now


class AgentSubscriptionQuerySet(auto_prefetch.QuerySet):
    """
    Queryset for AgentSubscription model.
    """

    def active(self) -> "AgentSubscriptionQuerySet":
        """Currently active subscriptions."""
        return self.filter(is_active=True)

    def expired(self) -> "AgentSubscriptionQuerySet":
        """
        Paid subscriptions whose end_date has passed.
        FREE tier (end_date=None) is intentionally excluded.
        """
        return self.filter(
            is_active=True,
            end_date__isnull=False,
            end_date__lt=Now(),
        )

    def free_tier(self) -> "AgentSubscriptionQuerySet":
        from core.helpers.enums import SubscriptionPlan
        return self.filter(plan=SubscriptionPlan.FREE.value)

    def paid(self) -> "AgentSubscriptionQuerySet":
        from core.helpers.enums import SubscriptionPlan
        return self.exclude(plan=SubscriptionPlan.FREE.value)

    def for_agent(self, agent) -> "AgentSubscriptionQuerySet":
        return self.filter(agent=agent)

    def with_agent_relations(self) -> "AgentSubscriptionQuerySet":
        return self.select_related(
            "agent",
            "agent__user",
        )


class FeaturedListingQuerySet(auto_prefetch.QuerySet):
    """
    Queryset for FeaturedListing model.
    """

    def active(self) -> "FeaturedListingQuerySet":
        """Currently active boosts that have not expired."""
        return self.filter(
            is_active=True,
            end_date__isnull=False,
            end_date__gte=Now(),
        )

    def expired(self) -> "FeaturedListingQuerySet":
        """Active records whose end_date has passed."""
        return self.filter(
            is_active=True,
            end_date__isnull=False,
            end_date__lt=Now(),
        )

    def for_agent(self, agent) -> "FeaturedListingQuerySet":
        return self.filter(agent=agent)

    def for_property(self, property_id: str) -> "FeaturedListingQuerySet":
        return self.filter(property_id=property_id)

    def with_relations(self) -> "FeaturedListingQuerySet":
        """
        Eager-loads all related data needed for serialization.
        Prevents N+1 on property title, agent name, etc.
        """
        return self.select_related(
            "property",
            "agent",
            "agent__user",
        )

    def active_count_for_agent(self, agent) -> int:
        """
        Returns count of active boosts for an agent.
        Used for plan limit enforcement — single DB hit.
        """
        return self.active().for_agent(agent).count()
