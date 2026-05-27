from __future__ import annotations

from django.db import transaction
from rest_framework.exceptions import NotFound

from core.applications.property.models import Property
from core.applications.users.models import AgentProfile
from core.helpers.enums import VerificationStatusChoices


def get_all_agents(
    *,
    verification_status: str | None = None,
    agent_type: str | None = None,
    search: str | None = None,
    ordering: str = "-created_at",
):
    """
    Returns a queryset of all agents for the admin management table.
    Supports filtering by verification status, agent type, and search.
    """
    from django.db.models import Count, Q

    allowed_ordering = {
        "created_at", "-created_at",
        "rating", "-rating",
        "verified", "-verified",
    }

    qs = (
        AgentProfile.objects
        .select_related("user")
        .prefetch_related("properties")
        .annotate(property_count=Count("properties", distinct=True))
    )

    if verification_status:
        qs = qs.filter(verification_status=verification_status)
    if agent_type:
        qs = qs.filter(agent_type=agent_type)
    if search:
        qs = qs.filter(
            Q(user__first_name_field__icontains=search)
            | Q(user__last_name_field__icontains=search)
            | Q(user__email__icontains=search)
            | Q(company_name__icontains=search)
        )

    if ordering not in allowed_ordering:
        ordering = "-created_at"

    return qs.order_by(ordering)


def get_agent_detail(*, agent_id: str) -> AgentProfile:
    try:
        return (
            AgentProfile.objects
            .select_related("user")
            .prefetch_related("properties")
            .get(pk=agent_id)
        )
    except AgentProfile.DoesNotExist:
        raise NotFound("Agent not found.")


def verify_agent(*, agent_id: str, verification_status: str, rejection_reason: str = "") -> AgentProfile:
    """
    Approve, decline, or revoke an agent's verification.
    Sets ``verified=True`` only on APPROVED status.
    """
    agent = get_agent_detail(agent_id=agent_id)

    with transaction.atomic():
        agent.verification_status = verification_status
        agent.verified = verification_status == VerificationStatusChoices.VERIFIED

        if verification_status == VerificationStatusChoices.REJECTED and rejection_reason:
            # Store reason in description temporarily or extend model later
            agent.description = (
                f"[REJECTED]: {rejection_reason}\n\n"
                + (agent.description or "")
            ).strip()

        agent.save(update_fields=["verification_status", "verified", "description", "updated_at"])

    return agent


def remove_agent(*, agent_id: str) -> None:
    """
    Soft-removes an agent by deactivating their user account.
    Does not hard delete — preserves audit trail and property history.
    """
    agent = get_agent_detail(agent_id=agent_id)
    with transaction.atomic():
        agent.user.is_active = False
        agent.user.save(update_fields=["is_active"])
        agent.verified = False
        agent.verification_status = VerificationStatusChoices.REVOKED
        agent.save(update_fields=["verified", "verification_status", "updated_at"])


def get_agent_properties(*, agent_id: str, visible: bool | None = None):
    """
    All properties for a given agent, for admin review.
    Optionally filter by visibility.
    """
    get_agent_detail(agent_id=agent_id)  # raises NotFound if missing

    qs = (
        Property.objects
        .filter(agent_id=agent_id)
        .select_related("agent", "agent__user")
        .prefetch_related("images", "amenities")
    )

    if visible is not None:
        qs = qs.filter(visible=visible)

    return qs.order_by("-created_at")


def moderate_property(*, property_id: str, validated_data: dict) -> Property:
    """
    Admin moderation of a property — toggle visibility, availability, featured.
    """
    try:
        prop = Property.objects.get(pk=property_id)
    except Property.DoesNotExist:
        raise NotFound("Property not found.")

    with transaction.atomic():
        for attr, value in validated_data.items():
            setattr(prop, attr, value)
        prop.save(update_fields=[*validated_data.keys(), "updated_at"])

    return prop


def get_all_properties(
    *,
    visible: bool | None = None,
    is_available: bool | None = None,
    property_listing: str | None = None,
    search: str | None = None,
    ordering: str = "-created_at",
):
    """
    Platform-wide property list for admin overview.
    """
    from django.db.models import Q

    allowed_ordering = {
        "created_at", "-created_at",
        "price", "-price",
        "title", "-title",
    }

    qs = (
        Property.objects
        .select_related("agent", "agent__user")
        .prefetch_related("images")
    )

    if visible is not None:
        qs = qs.filter(visible=visible)
    if is_available is not None:
        qs = qs.filter(is_available=is_available)
    if property_listing:
        qs = qs.filter(property_listing=property_listing)
    if search:
        qs = qs.filter(
            Q(title__icontains=search)
            | Q(location__icontains=search)
            | Q(agent__user__email__icontains=search)
        )

    if ordering not in allowed_ordering:
        ordering = "-created_at"

    return qs.order_by(ordering)
