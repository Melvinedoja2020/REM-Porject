from __future__ import annotations

from rest_framework.permissions import SAFE_METHODS
from rest_framework.permissions import BasePermission

from core.helpers.enums import VerificationStatusChoices

# ---------------------------------------------------------------------------
# Agent helpers
# ---------------------------------------------------------------------------


def _agent_profile(user):
    """
    Safely returns the user's AgentProfile or None.
    """
    return getattr(user, "agent_profile", None)


def _is_authenticated(user) -> bool:
    """
    Returns True when the user exists and is authenticated.
    """
    return bool(user and user.is_authenticated)


def _is_agent(user) -> bool:
    """
    Returns True when the authenticated user has an AgentProfile.
    """
    return bool(
        _is_authenticated(user)
        and _agent_profile(user) is not None
    )


def _is_verified_agent(user) -> bool:
    """
    Returns True when the authenticated user:
    - has an AgentProfile
    - and the profile verification status is VERIFIED
    """
    profile = _agent_profile(user)

    return bool(
        profile
        and profile.verification_status
        == VerificationStatusChoices.VERIFIED
    )


def _agent_pk(user) -> str | None:
    """
    Returns the authenticated agent profile PK as a string.

    Returns None when the user has no AgentProfile.
    """
    profile = _agent_profile(user)
    return str(profile.pk) if profile else None


# ---------------------------------------------------------------------------
# Object ownership helpers
# ---------------------------------------------------------------------------


def _owner_id(obj) -> str | None:
    """
    Resolves the owning user PK from an object.

    Optimized to use ``obj.user_id`` first to avoid unnecessary joins,
    then falls back to ``obj.user.pk``.
    """
    user_id = getattr(obj, "user_id", None)

    if user_id is None:
        user = getattr(obj, "user", None)
        user_id = getattr(user, "pk", None)

    return str(user_id) if user_id is not None else None


def _object_agent_id(obj) -> str | None:
    """
    Resolves the direct agent PK from an object.

    Optimized to use ``obj.agent_id`` first, then ``obj.agent.pk``.
    """
    agent_id = getattr(obj, "agent_id", None)

    if agent_id is None:
        agent = getattr(obj, "agent", None)
        agent_id = getattr(agent, "pk", None)

    return str(agent_id) if agent_id is not None else None


def _property_agent_id(obj) -> str | None:
    """
    Resolves the agent PK that owns the property linked to an object.

    Supports:
    - Lead -> property_link -> agent
    - PropertyViewing -> property -> agent

    Related objects should be select_related before permission checks
    to avoid additional queries.
    """
    property_obj = (
        getattr(obj, "property_link", None)
        or getattr(obj, "property", None)
    )

    if property_obj is None:
        return None

    agent_id = getattr(property_obj, "agent_id", None)

    if agent_id is None:
        agent = getattr(property_obj, "agent", None)
        agent_id = getattr(agent, "pk", None)

    return str(agent_id) if agent_id is not None else None


# ---------------------------------------------------------------------------
# Atomic permission classes
# ---------------------------------------------------------------------------


class IsAgentUser(BasePermission):
    """
    Grants access only to authenticated users with an AgentProfile.
    """

    message = "You must have an agent profile to perform this action."

    def has_permission(self, request, view) -> bool:
        return _is_agent(request.user)

    def has_object_permission(self, request, view, obj) -> bool:
        return _is_agent(request.user)


class IsVerifiedAgent(BasePermission):
    """
    Grants access only to verified agent accounts.
    """

    message = "Your agent account must be verified."

    def has_permission(self, request, view) -> bool:
        return _is_verified_agent(request.user)

    def has_object_permission(self, request, view, obj) -> bool:
        return _is_verified_agent(request.user)


class IsPropertyOwnerAgent(BasePermission):
    """
    Object-level permission that grants access only to the verified
    agent who owns the property.

    Used for:
    - update
    - partial_update
    - destroy
    """

    message = (
        "Only the verified agent who listed this property "
        "may modify it."
    )

    def has_permission(self, request, view) -> bool:
        return _is_verified_agent(request.user)

    def has_object_permission(self, request, view, obj) -> bool:
        return (
            _is_verified_agent(request.user)
            and _object_agent_id(obj) == _agent_pk(request.user)
        )


class IsLeadOwnerOrPropertyAgent(BasePermission):
    """
    Object-level permission for Lead retrieve.

    Grants access when the requesting user is:
      • the user who created the lead (lead.user_id), OR
      • the agent who owns the property the lead is about
        (lead.property_link.agent_id)

    Both ``property_link`` and ``property_link__agent`` must be
    select_related by the queryset before object-level check is called.
    """

    message = "You do not have permission to access this lead."

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        # Lead owner.
        if _owner_id(obj) == str(user.pk):
            return True
        # Property's agent.
        return _property_agent_id(obj) == _agent_pk(user)


class IsLeadPropertyAgent(BasePermission):
    """
    Object-level permission for Lead status updates.

    Grants access only to the agent who owns the property that the
    lead is about — not the lead's user, not any other agent.

    Used exclusively on the ``update_status`` @action.
    """

    message = "Only the property agent may update lead status."

    def has_permission(self, request, view) -> bool:
        return _is_agent(request.user)

    def has_object_permission(self, request, view, obj) -> bool:
        return _property_agent_id(obj) == _agent_pk(request.user)


class IsViewingOwnerOrPropertyAgent(BasePermission):
    """
    Object-level permission for PropertyViewing retrieve / cancel.

    Grants access when the requesting user is:
      • the user who booked the viewing (viewing.user_id), OR
      • the agent who owns the property being viewed
        (viewing.property.agent_id)

    ``property`` and ``property__agent`` must be select_related before
    the object-level check is invoked.
    """

    message = "You do not have permission to access this viewing."

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj) -> bool:
        user = request.user
        # Booking user.
        if _owner_id(obj) == str(user.pk):
            return True
        # Property's agent.
        return _property_agent_id(obj) == _agent_pk(user)


class IsObjectOwner(BasePermission):
    """
    Generic object-level permission.
    Grants access when obj.user_id == request.user.pk.

    Used for FavoriteProperty and PropertySubscription — resources that
    belong exclusively to the user who created them.

    The queryset is already scoped to request.user in both ViewSets so
    this acts as a defence-in-depth guard against direct PK enumeration.
    """

    message = "You can only manage your own records."

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj) -> bool:
        return _owner_id(obj) == str(request.user.pk)
