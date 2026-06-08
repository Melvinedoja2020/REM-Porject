# core/applications/subscriptions/features.py

from __future__ import annotations

from core.helpers.custom_exceptions import SubscriptionLimitError
from core.helpers.enums import SubscriptionPlan


_FEATURE_LABELS: dict[str, str] = {
    "properties":          "property listings",
    "featured_listings":   "featured listing boosts",
    "boost_duration_days": "boost duration",
    "images_per_property": "images per property",
    "leads_per_month":     "leads per month",
}

FEATURE_LIMITS: dict[str, dict[str, int | None]] = {
    SubscriptionPlan.FREE.value: {
        "properties":          5,
        "featured_listings":   0,    # boosting completely disabled
        "boost_duration_days": 0,    # no boost duration — disabled
        "images_per_property": 3,
        "leads_per_month":     10,
    },
    SubscriptionPlan.BASIC.value: {
        "properties":          20,
        "featured_listings":   10,   # up to 10 active boosts at a time
        "boost_duration_days": 7,    # each boost lasts 7 days
        "images_per_property": 8,
        "leads_per_month":     50,
    },
    SubscriptionPlan.PREMIUM.value: {
        "properties":          40,
        "featured_listings":   20,
        "boost_duration_days": 14,   # each boost lasts 14 days
        "images_per_property": 15,
        "leads_per_month":     200,
    },
    SubscriptionPlan.ENTERPRISE.value: {
        "properties":          None, # unlimited
        "featured_listings":   None, # unlimited
        "boost_duration_days": 30,   # each boost lasts 30 days
        "images_per_property": None, # unlimited
        "leads_per_month":     None, # unlimited
    },
}


def _resolve_plan(plan: str | SubscriptionPlan) -> str:
    """
    Normalise a plan input to a plain string matching FEATURE_LIMITS keys.

    Accepts either a raw DB string (``"Free"``) or a ``SubscriptionPlan``
    enum member. Falls back to FREE for unrecognised values so unknown
    plans are always treated as the most restrictive tier.

    Args:
        plan: Raw plan string from the database or a SubscriptionPlan member.

    Returns:
        A plain string matching one of the FEATURE_LIMITS keys.
    """
    if isinstance(plan, SubscriptionPlan):
        plan = plan.value

    if not isinstance(plan, str):
        return SubscriptionPlan.FREE.value

    mapping = {
        "free":       SubscriptionPlan.FREE.value,
        "basic":      SubscriptionPlan.BASIC.value,
        "premium":    SubscriptionPlan.PREMIUM.value,
        "enterprise": SubscriptionPlan.ENTERPRISE.value,
    }

    return mapping.get(plan.strip().lower(), SubscriptionPlan.FREE.value)


def get_limit(plan: str | SubscriptionPlan, feature: str) -> int | None:
    """
    Return the cap for a given plan and feature combination.

    Args:
        plan:    Subscription plan — raw DB string or SubscriptionPlan member.
        feature: Feature key e.g. ``"properties"``, ``"featured_listings"``.

    Returns:
        ``None`` if the feature is unlimited for this plan.
        ``0``    if the feature is completely disabled for this plan.
        ``int``  the hard cap that must not be exceeded.

    Example::

        limit = get_limit("Basic", "properties")
        # → 20
    """
    resolved = _resolve_plan(plan)
    limits = FEATURE_LIMITS.get(
        resolved,
        FEATURE_LIMITS[SubscriptionPlan.FREE.value],  # safe fallback
    )
    return limits.get(feature, 0)


def get_boost_duration(plan: str | SubscriptionPlan) -> int:
    """
    Return the boost duration in days for the given plan.

    Used by ``boost_property()`` to calculate ``end_date`` when
    creating a FeaturedListing.

    Args:
        plan: Subscription plan — raw DB string or SubscriptionPlan member.

    Returns:
        Number of days a boost lasts on this plan.
        Returns ``0`` if boosting is disabled (FREE tier).

    Example::

        days = get_boost_duration("Premium")
        # → 14
    """
    return get_limit(plan, "boost_duration_days") or 0


def is_feature_available(plan: str | SubscriptionPlan, feature: str) -> bool:
    """
    Return ``True`` when the feature is accessible on the given plan.

    A limit of ``0`` means the feature is explicitly disabled.
    ``None`` means unlimited (always available).
    Any positive integer means capped but available.

    Args:
        plan:    Subscription plan — raw DB string or SubscriptionPlan member.
        feature: Feature key to check.

    Returns:
        ``True`` if the feature can be used; ``False`` if disabled.

    Example::

        if not is_feature_available(plan, "featured_listings"):
            raise SubscriptionLimitError("Upgrade to boost properties.")
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
    Enforce a feature cap, raising ``SubscriptionLimitError`` when hit.

    This is the single authoritative enforcement point used by the
    service layer. All callers should prefer this over manual
    ``get_limit`` + ``if`` checks to keep error messages consistent.

    Args:
        plan:          Subscription plan — raw DB string or SubscriptionPlan member.
        feature:       Feature key e.g. ``"properties"``.
        current_count: How many the agent currently has (before this new one).
        label:         Optional human-readable feature name for the error message.
                       Falls back to ``_FEATURE_LABELS[feature]`` then ``feature``.

    Raises:
        SubscriptionLimitError: When feature is disabled or limit is reached.

    Example::

        check_limit(
            plan=agent.current_subscription.plan,
            feature="properties",
            current_count=agent.properties.count(),
        )
    """
    limit = get_limit(plan, feature)
    resolved_plan = _resolve_plan(plan)
    feature_label = label or _FEATURE_LABELS.get(feature, feature)

    # Feature completely disabled for this plan
    if limit == 0:
        raise SubscriptionLimitError(
            f"The {feature_label} feature is not available on the "
            f"{resolved_plan} plan. Please upgrade your subscription."
        )

    # Unlimited — nothing to enforce
    if limit is None:
        return

    # Hard cap reached
    if current_count >= limit:
        raise SubscriptionLimitError(
            f"You have reached your {feature_label} limit ({limit}) "
            f"for the {resolved_plan} plan. Please upgrade your subscription."
        )
