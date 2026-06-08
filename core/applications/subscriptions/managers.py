# core/applications/subscriptions/managers.py

from __future__ import annotations

import auto_prefetch

from core.applications.subscriptions.querysets.subscription_querysets import (
    AgentSubscriptionQuerySet,
)
from core.applications.subscriptions.querysets.subscription_querysets import (
    FeaturedListingQuerySet,
)


class AgentSubscriptionManager(auto_prefetch.Manager):
    def get_queryset(self) -> AgentSubscriptionQuerySet:
        return AgentSubscriptionQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()

    def expired(self):
        return self.get_queryset().expired()


class FeaturedListingManager(auto_prefetch.Manager):
    def get_queryset(self) -> FeaturedListingQuerySet:
        return FeaturedListingQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()

    def expired(self):
        return self.get_queryset().expired()

    def with_relations(self):
        return self.get_queryset().with_relations()
