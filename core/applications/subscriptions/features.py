from __future__ import annotations

from django.core.exceptions import ValidationError

from core.helpers.custom_exceptions import SubscriptionLimitError
from core.helpers.enums import SubscriptionPlan

_FEATURE_LABELS: dict[str, str] = {
    "properties":          "property listings",
    "featured_listings":   "featured listing boosts",
    "images_per_property": "images per property",
    "leads_per_month":     "leads per month",
}

FEATURE_LIMITS: dict[str, dict[str, int | None]] = {
    SubscriptionPlan.FREE.value: {
        "properties":          10,     # one listing only
        "featured_listings":   5,     # boosting disabled
        "images_per_property": 3,     # minimal gallery
        "leads_per_month":     10,    # limited enquiries
    },
    SubscriptionPlan.BASIC.value: {
        "properties":          20,
        "featured_listings":   10,     # one active boost at a time
        "images_per_property": 8,
        "leads_per_month":     50,
    },
    SubscriptionPlan.PREMIUM.value: {
        "properties":          50,
        "featured_listings":   20,
        "images_per_property": 15,
        "leads_per_month":     200,
    },
    SubscriptionPlan.ENTERPRISE.value: {
        "properties":          None,  # unlimited
        "featured_listings":   None,  # unlimited
        "images_per_property": None,  # unlimited
        "leads_per_month":     None,  # unlimited
    },
}


def _resolve_plan(plan: str | SubscriptionPlan) -> str:
    """
    Normalize a plan input to a valid SubscriptionPlan value string.
    """

    if isinstance(plan, SubscriptionPlan):
        plan = plan.value

    if not isinstance(plan, str):
        return SubscriptionPlan.FREE.value

    normalized = plan.strip().lower()

    mapping = {
        "free": SubscriptionPlan.FREE.value,
        "basic": SubscriptionPlan.BASIC.value,
        "premium": SubscriptionPlan.PREMIUM.value,
        "enterprise": SubscriptionPlan.ENTERPRISE.value,
    }

    return mapping.get(normalized, SubscriptionPlan.FREE.value)


def get_limit(plan: str | SubscriptionPlan, feature: str) -> int | None:
    """
    Get the limit for a given feature on the specified plan.
    """

    resolved = _resolve_plan(plan)

    limits = FEATURE_LIMITS.get(
        resolved,
        FEATURE_LIMITS[SubscriptionPlan.FREE.value],
    )

    return limits.get(feature, 0)


def is_feature_available(plan: str | SubscriptionPlan, feature: str) -> bool:
    """
    Return ``True`` when the feature is accessible on the given plan.

    A limit of ``0`` means the feature is explicitly disabled; ``None``
    means unlimited (always available); any positive integer means capped
    but available.

    Args:
        plan:    Subscription plan — raw DB string or SubscriptionPlan member.
        feature: Feature key to check.

    Returns:
        ``True`` if the feature can be used at all; ``False`` if it is
        disabled (limit == 0) for this plan.

    Example::

        if not is_feature_available(agent_plan, "featured_listings"):
            raise ValidationError("Upgrade your plan to boost properties.")
    """
    limit = get_limit(plan, feature)
    return limit is None or limit > 0


def check_limit(
    plan: str | SubscriptionPlan,
    feature: str,
    current_count: int,
    label: str | None = None,
) -> None:
    """
    Enforce a feature cap for a subscription plan.

    Raises:
        SubscriptionLimitError: when the feature is disabled or limit exceeded.
    """

    limit = get_limit(plan, feature)
    resolved_plan = _resolve_plan(plan)

    feature_label = label or _FEATURE_LABELS.get(feature, feature)

    # FEATURE DISABLED
    if limit == 0:
        msg = f"Your {feature_label} feature is not available on the {resolved_plan} plan."
        raise SubscriptionLimitError(
            msg,
        )

    # UNLIMITED (Enterprise or similar)
    if limit is None:
        return

    # LIMIT REACHED
    if current_count >= limit:
        msg = (
            f"You have reached your {feature_label} limit ({limit}) "
            f"for the {resolved_plan} plan. Please upgrade your subscription."
        )
        raise SubscriptionLimitError(
            msg,
        )
