from __future__ import annotations

from rest_framework.permissions import SAFE_METHODS
from rest_framework.permissions import AllowAny
from rest_framework.permissions import BasePermission
from rest_framework.permissions import IsAuthenticated




def _is_agent(user) -> bool:
    """True when the user is authenticated and has a non-null AgentProfile."""
    return bool(
        user
        and user.is_authenticated
        and getattr(user, "agent_profile", None) is not None
    )


def _agent_pk(user) -> str | None:
    """Returns str(agent.pk) or None — safe even when no profile exists."""
    profile = getattr(user, "agent_profile", None)
    return str(profile.pk) if profile else None


def _owner_id(obj) -> str | None:
    """
    Resolves the owning user PK from an object.
    Tries ``obj.user_id`` first (avoids a JOIN), then ``obj.user.pk``.
    """
    uid = getattr(obj, "user_id", None)
    if uid is None:
        user = getattr(obj, "user", None)
        uid = getattr(user, "pk", None)
    return str(uid) if uid is not None else None


def _object_agent_id(obj) -> str | None:
    """
    Resolves the agent PK from an object.
    Tries ``obj.agent_id`` first, then ``obj.agent.pk``.
    """
    aid = getattr(obj, "agent_id", None)
    if aid is None:
        agent = getattr(obj, "agent", None)
        aid = getattr(agent, "pk", None)
    return str(aid) if aid is not None else None


def _property_agent_id(obj) -> str | None:
    """
    Resolves the agent PK that owns the *property* linked to an object.
    Works for Lead (obj.property_link.agent_id) and PropertyViewing
    (obj.property.agent_id).  Both relations must be select_related by
    the queryset before this is called.
    """
    # Lead  → property_link → agent_id
    prop = getattr(obj, "property_link", None) or getattr(obj, "property", None)
    if prop is None:
        return None
    aid = getattr(prop, "agent_id", None)
    if aid is None:
        agent = getattr(prop, "agent", None)
        aid = getattr(agent, "pk", None)
    return str(aid) if aid is not None else None


# ---------------------------------------------------------------------------
# Atomic permission classes
# ---------------------------------------------------------------------------


class IsAgentUser(BasePermission):
    """
    Grants access only to authenticated users with an AgentProfile.

    Used as a standalone permission on views where the entire endpoint
    is agent-only (e.g. AgentPropertyListView).

    Object-level: always True when request-level passes, because agent
    identity is the only requirement — object ownership is checked
    separately by IsPropertyOwnerAgent where needed.
    """

    message = "You must have an agent profile to perform this action."

    def has_permission(self, request, view) -> bool:
        return _is_agent(request.user)

    def has_object_permission(self, request, view, obj) -> bool:
        return _is_agent(request.user)


class IsPropertyOwnerAgent(BasePermission):
    """
    Object-level permission.
    Grants write access only to the agent who owns the property.

    Request-level: requires authentication + an agent profile.
    Object-level:  obj.agent_id must match request.user.agent_profile.pk.

    Used on PropertyViewSet for update / partial_update / destroy.
    """

    message = "Only the agent who listed this property may modify it."

    def has_permission(self, request, view) -> bool:
        return _is_agent(request.user)

    def has_object_permission(self, request, view, obj) -> bool:
        return _object_agent_id(obj) == _agent_pk(request.user)


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
