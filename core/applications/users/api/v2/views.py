# core/applications/users/api/admin_views.py

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.applications.users.api.v2.schemas import AdminAgentViewSetSchema
from core.applications.users.api.v2.schemas import AdminPropertyViewSetSchema
from core.applications.users.api.v2.serializers import AdminAgentDetailSerializer
from core.applications.users.api.v2.serializers import AdminAgentListSerializer
from core.applications.users.api.v2.serializers import AdminAgentVerificationSerializer
from core.applications.users.api.v2.serializers import AdminPropertyDetailSerializer
from core.applications.users.api.v2.serializers import AdminPropertyListSerializer
from core.applications.users.api.v2.serializers import AdminPropertyModerationSerializer
from core.applications.users.permissions import IsAdminUser
from core.applications.users.services import admin_services as services


def _parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    return value.lower() in ("true", "1", "yes")

@AdminAgentViewSetSchema
class AdminAgentViewSet(ViewSet):
    """
    Admin endpoints for agent management.

    All endpoints require staff/admin privileges.
    Business logic is fully delegated to admin_services.
    """
    permission_classes = [IsAdminUser]

    def list(self, request: Request) -> Response:
        """Paginated list of all agents with filtering support."""
        params = request.query_params
        qs = services.get_all_agents(
            verification_status=params.get("verification_status"),
            agent_type=params.get("agent_type"),
            search=params.get("search"),
            ordering=params.get("ordering", "-created_at"),
        )
        serializer = AdminAgentListSerializer(qs, many=True)
        return Response(serializer.data)

    def retrieve(self, request: Request, pk=None) -> Response:
        """Full agent detail including sensitive fields."""
        agent = services.get_agent_detail(agent_id=pk)
        serializer = AdminAgentDetailSerializer(agent)
        return Response(serializer.data)

    @action(detail=True, methods=["patch"], url_path="verify")
    def verify(self, request: Request, pk=None) -> Response:
        """
        Approve, decline, or revoke an agent's verification status.
        PATCH /admin/agents/{id}/verify/
        """
        serializer = AdminAgentVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        agent = services.verify_agent(
            agent_id=pk,
            verification_status=serializer.validated_data["verification_status"],
            rejection_reason=serializer.validated_data.get("rejection_reason", ""),
        )
        return Response(
            AdminAgentDetailSerializer(agent).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["delete"], url_path="remove")
    def remove(self, request: Request, pk=None) -> Response:
        """
        Soft-remove an agent — deactivates account and revokes verification.
        DELETE /admin/agents/{id}/remove/
        """
        services.remove_agent(agent_id=pk)
        return Response(
            {"detail": "Agent has been deactivated and verification revoked."},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="properties")
    def properties(self, request: Request, pk=None) -> Response:
        """
        All properties listed by a specific agent.
        GET /admin/agents/{id}/properties/
        """
        qs = services.get_agent_properties(
            agent_id=pk,
            visible=_parse_bool(request.query_params.get("visible")),
        )
        serializer = AdminPropertyListSerializer(qs, many=True)
        return Response(serializer.data)

@AdminPropertyViewSetSchema
class AdminPropertyViewSet(ViewSet):
    """
    Admin endpoints for platform-wide property management.

    All endpoints require staff/admin privileges.
    """
    permission_classes = [IsAdminUser]

    def list(self, request: Request) -> Response:
        """Platform-wide property list with filtering."""
        params = request.query_params
        qs = services.get_all_properties(
            visible=_parse_bool(params.get("visible")),
            is_available=_parse_bool(params.get("is_available")),
            property_listing=params.get("property_listing"),
            search=params.get("search"),
            ordering=params.get("ordering", "-created_at"),
        )
        serializer = AdminPropertyListSerializer(qs, many=True)
        return Response(serializer.data)

    def retrieve(self, request: Request, pk=None) -> Response:
        """Full property detail for admin review."""
        try:
            from core.applications.property.models import Property
            prop = (
                Property.objects
                .select_related("agent", "agent__user")
                .prefetch_related("images", "amenities")
                .get(pk=pk)
            )
        except Property.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AdminPropertyDetailSerializer(prop)
        return Response(serializer.data)

    @action(detail=True, methods=["patch"], url_path="moderate")
    def moderate(self, request: Request, pk=None) -> Response:
        """
        Toggle property visibility, availability, or featured status.
        PATCH /admin/properties/{id}/moderate/
        """
        serializer = AdminPropertyModerationSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        prop = services.moderate_property(
            property_id=pk,
            validated_data=serializer.validated_data,
        )
        return Response(
            AdminPropertyDetailSerializer(prop).data,
            status=status.HTTP_200_OK,
        )
