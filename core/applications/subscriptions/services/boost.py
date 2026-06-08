from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from django.db import transaction as db_transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound

from core.applications.subscriptions.features import check_limit
from core.applications.subscriptions.features import get_boost_duration
from core.applications.subscriptions.features import get_limit

if TYPE_CHECKING:
    from core.applications.subscriptions.models import AgentSubscription
    from core.applications.subscriptions.models import FeaturedListing

logger = logging.getLogger(__name__)



def _get_agent_plan(agent) -> str:
    """
    Resolve the agent's current subscription plan as a raw string.
    Falls back to FREE if no subscription is assigned or active.
    """
    from core.helpers.enums import SubscriptionPlan

    subscription = getattr(agent, "current_subscription", None)
    if subscription and subscription.is_valid():
        return subscription.plan
    return SubscriptionPlan.FREE.value


def _trim_excess_boosts(agent, new_plan: str) -> None:
    """
    After a plan downgrade, remove the oldest active boosts that exceed
    the new plan's ``featured_listings`` limit.

    Called inside ``upgrade_subscription()`` within the same transaction.

    Args:
        agent:    AgentProfile instance.
        new_plan: The plan the agent is moving to (raw string value).
    """
    from core.applications.property.models import Property
    from core.applications.subscriptions.models import FeaturedListing

    new_limit = get_limit(new_plan, "featured_listings")

    # Unlimited on new plan — nothing to trim
    if new_limit is None:
        return

    active_boosts = (
        FeaturedListing.objects
        .active()
        .for_agent(agent)
        .order_by("start_date")  # oldest first — remove these first
    )

    total = active_boosts.count()

    # Within new limit — nothing to trim
    if total <= new_limit:
        return

    excess_count = total - new_limit

    # IDs of oldest boosts to remove
    excess_ids = list(
        active_boosts.values_list("id", flat=True)[:excess_count]
    )

    # Capture affected property IDs before delete
    affected_property_ids = list(
        FeaturedListing.objects
        .filter(id__in=excess_ids)
        .values_list("property_id", flat=True)
    )

    FeaturedListing.objects.filter(id__in=excess_ids).delete()

    # Only unfeature properties with no remaining active boosts
    still_boosted_ids = set(
        FeaturedListing.objects
        .active()
        .filter(property_id__in=affected_property_ids)
        .values_list("property_id", flat=True)
    )

    to_unfeature = [
        pk for pk in affected_property_ids
        if pk not in still_boosted_ids
    ]

    if to_unfeature:
        Property.objects.filter(pk__in=to_unfeature).update(is_featured=False)

    logger.info(
        "Trimmed %s excess boost(s) for agent %s after plan change to %s.",
        excess_count,
        agent.pk,
        new_plan,
    )

def boost_property(*, agent, property_id: str) -> "FeaturedListing":
    """
    Features a property within the agent's subscription allowance.

    No separate payment required — featuring is covered by the agent's
    active subscription tier.

    ``end_date`` is calculated from the plan's ``boost_duration_days``
    in ``FEATURE_LIMITS`` — no hardcoded durations anywhere.

    Enforces:
      - Property must belong to the agent
      - Agent's plan must allow featured listings (limit > 0)
      - Agent must not have exceeded their active boost limit

    Args:
        agent:       AgentProfile instance of the authenticated agent.
        property_id: PK of the property to feature.

    Returns:
        The newly created and saved FeaturedListing instance.

    Raises:
        NotFound:              Property not found or doesn't belong to agent.
        SubscriptionLimitError: Agent has hit their featured listing limit.
    """
    from core.applications.property.models import Property
    from core.applications.subscriptions.models import FeaturedListing

    try:
        prop = (
            Property.objects
            .select_related("agent")
            .get(pk=property_id, agent=agent)
        )
    except Property.DoesNotExist:
        raise NotFound("Property not found or does not belong to this agent.")

    plan = _get_agent_plan(agent)

    # Enforce featured listing limit — single aggregated count query
    active_boost_count = (
        FeaturedListing.objects
        .active()
        .for_agent(agent)
        .count()
    )

    check_limit(
        plan=plan,
        feature="featured_listings",
        current_count=active_boost_count,
    )

    # Calculate end_date from plan config — no hardcoding
    boost_days = get_boost_duration(plan)
    end_date = timezone.now() + timedelta(days=boost_days)

    with db_transaction.atomic():
        featured = FeaturedListing(
            property=prop,
            agent=agent,
            end_date=end_date,
            boost_duration=boost_days,
        )
        featured.full_clean()
        featured.save()

        Property.objects.filter(pk=prop.pk).update(is_featured=True)

    logger.info(
        "Property %s boosted by agent %s for %s days (expires %s).",
        prop.pk,
        agent.pk,
        boost_days,
        end_date.date(),
    )

    return featured


def unboost_property(*, agent, property_id: str) -> None:
    """
    Removes the active featured listing for a property owned by the agent.

    Args:
        agent:       AgentProfile instance of the authenticated agent.
        property_id: PK of the property to unfeature.

    Raises:
        NotFound: No active boost found for this property and agent.
    """
    from core.applications.property.models import Property
    from core.applications.subscriptions.models import FeaturedListing

    deleted_count, _ = (
        FeaturedListing.objects
        .active()
        .for_agent(agent)
        .for_property(property_id)
        .delete()
    )

    if not deleted_count:
        raise NotFound("No active featured listing found for this property.")

    # Only unfeature if no other active boosts remain for this property
    still_boosted = (
        FeaturedListing.objects
        .active()
        .for_property(property_id)
        .exists()
    )

    if not still_boosted:
        Property.objects.filter(pk=property_id).update(is_featured=False)

    logger.info(
        "Property %s unboosted by agent %s.",
        property_id,
        agent.pk,
    )


# ---------------------------------------------------------------------------
# Celery beat maintenance tasks
# ---------------------------------------------------------------------------

def deactivate_expired_boosts() -> int:
    """
    Deactivates FeaturedListing records whose end_date has passed and
    syncs the ``is_featured`` flag on affected Property rows.

    Called by Celery beat every 6 hours — never triggered by user actions.

    Returns:
        Count of deactivated featured listings.
    """
    from core.applications.property.models import Property
    from core.applications.subscriptions.models import FeaturedListing

    expired_qs = FeaturedListing.objects.expired()

    # Capture before update — queryset won't match after is_active flips
    expired_property_ids = list(
        expired_qs.values_list("property_id", flat=True)
    )
    count = expired_qs.count()

    expired_qs.update(is_active=False)

    # Only unfeature properties with no remaining active boosts
    still_boosted_ids = set(
        FeaturedListing.objects
        .active()
        .filter(property_id__in=expired_property_ids)
        .values_list("property_id", flat=True)
    )

    to_unfeature = [
        pk for pk in expired_property_ids
        if pk not in still_boosted_ids
    ]

    if to_unfeature:
        Property.objects.filter(pk__in=to_unfeature).update(is_featured=False)

    logger.info("Deactivated %s expired featured listing(s).", count)
    return count


def deactivate_expired_subscriptions() -> int:
    """
    Deactivates AgentSubscription records where end_date has passed and
    assigns a fresh FREE tier subscription to affected agents so they
    always have a valid ``current_subscription``.

    FREE tier subscriptions (end_date=None) are intentionally excluded.

    Called by Celery beat daily at midnight — never triggered by user actions.

    Returns:
        Count of deactivated subscriptions.
    """
    from core.applications.subscriptions.models import AgentSubscription
    from core.helpers.enums import SubscriptionPlan

    expired_qs = AgentSubscription.objects.expired().select_related("agent")
    count = expired_qs.count()

    for subscription in expired_qs:
        with db_transaction.atomic():
            subscription.is_active = False
            subscription.save(update_fields=["is_active", "updated_at"])

            # Assign fresh FREE tier so agent.current_subscription is never None
            free_sub = AgentSubscription.objects.create(
                agent=subscription.agent,
                plan=SubscriptionPlan.FREE.value,
                is_active=True,
                is_trial=False,
                amount_paid=0,
                end_date=None,  # FREE never expires
            )

            subscription.agent.current_subscription = free_sub
            subscription.agent.save(update_fields=["current_subscription", "updated_at"])

            # Trim boosts that now exceed FREE tier limit
            _trim_excess_boosts(subscription.agent, SubscriptionPlan.FREE.value)

    logger.info("Deactivated %s expired subscription(s).", count)
    return count


# ---------------------------------------------------------------------------
# Subscription upgrade
# ---------------------------------------------------------------------------

def upgrade_subscription(
    *,
    agent,
    new_plan: str,
    transaction_id: str,
    amount: float,
) -> "AgentSubscription":
    """
    Upgrades or downgrades an agent's subscription after Paystack payment.

    Flow:
      1. Validate new_plan is a recognised value
      2. Deactivate all current active subscriptions
      3. Create new subscription (model.save() sets end_date from PlanConfig)
      4. Update agent.current_subscription
      5. Trim excess boosts if downgrading

    Args:
        agent:          AgentProfile instance.
        new_plan:       Target plan value e.g. ``"Basic"``, ``"Premium"``.
        transaction_id: Paystack transaction reference for audit trail.
        amount:         Amount paid in NGN.

    Returns:
        The newly created AgentSubscription instance.

    Raises:
        ValidationError: If new_plan is not a recognised SubscriptionPlan value.
    """
    from django.core.exceptions import ValidationError
    from core.applications.subscriptions.models import AgentSubscription
    from core.helpers.enums import SubscriptionPlan

    if new_plan not in SubscriptionPlan.values:
        raise ValidationError(f"'{new_plan}' is not a valid subscription plan.")

    with db_transaction.atomic():
        # Deactivate all existing active subscriptions
        AgentSubscription.objects.filter(
            agent=agent,
            is_active=True,
        ).update(is_active=False)

        # Create new subscription — model.save() sets end_date from PlanConfig
        new_subscription = AgentSubscription.objects.create(
            agent=agent,
            plan=new_plan,
            is_active=True,
            is_trial=False,
            amount_paid=amount,
            transaction_id=transaction_id,
        )

        # Point agent to new subscription
        agent.current_subscription = new_subscription
        agent.save(update_fields=["current_subscription", "updated_at"])

        # Trim excess boosts if this is a downgrade
        _trim_excess_boosts(agent, new_plan)

    logger.info(
        "Agent %s moved to %s plan (transaction: %s, amount: %s).",
        agent.pk,
        new_plan,
        transaction_id,
        amount,
    )

    return new_subscription
