# core/applications/users/api/admin_schema.py

from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.utils import OpenApiTypes
from drf_spectacular.utils import extend_schema
from drf_spectacular.utils import extend_schema_view

from core.applications.users.api.v2.serializers import AdminAgentDetailSerializer
from core.applications.users.api.v2.serializers import AdminAgentListSerializer
from core.applications.users.api.v2.serializers import AdminAgentVerificationSerializer
from core.applications.users.api.v2.serializers import AdminPropertyDetailSerializer
from core.applications.users.api.v2.serializers import AdminPropertyListSerializer
from core.applications.users.api.v2.serializers import AdminPropertyModerationSerializer

AdminAgentViewSetSchema = extend_schema_view(
    list=extend_schema(
        summary="List All Agents",
        description="""
Admin-only. Returns all registered agents with filtering support.

Filters:
- `verification_status` — PENDING, APPROVED, REJECTED, REVOKED
- `agent_type` — agent classification
- `search` — name, email, or company
- `ordering` — created_at, rating, verified
        """,
        parameters=[
            OpenApiParameter("verification_status", OpenApiTypes.STR),
            OpenApiParameter("agent_type", OpenApiTypes.STR),
            OpenApiParameter("search", OpenApiTypes.STR),
            OpenApiParameter("ordering", OpenApiTypes.STR),
        ],
        responses={200: AdminAgentListSerializer(many=True)},
        tags=["Admin — Agents"],
    ),
    retrieve=extend_schema(
        summary="Get Agent Detail",
        description="Admin-only. Full agent profile including sensitive verification documents.",
        responses={200: AdminAgentDetailSerializer()},
        tags=["Admin — Agents"],
    ),
    verify=extend_schema(
        summary="Verify / Decline / Revoke Agent",
        description="""
Admin-only. Update an agent's verification status.

- `APPROVED` → sets `verified=True`
- `REJECTED` → requires `rejection_reason`
- `REVOKED` → removes verification from a previously approved agent
        """,
        request=AdminAgentVerificationSerializer(),
        responses={200: AdminAgentDetailSerializer()},
        tags=["Admin — Agents"],
    ),
    remove=extend_schema(
        summary="Remove Agent",
        description="""
Admin-only. Soft-removes an agent:
- Deactivates their user account (`is_active=False`)
- Revokes verification status
- Preserves all property listings and audit history
        """,
        responses={200: None},
        tags=["Admin — Agents"],
    ),
    properties=extend_schema(
        summary="Get Agent Properties",
        description="Admin-only. All properties listed by a specific agent. Filterable by visibility.",
        parameters=[
            OpenApiParameter("visible", OpenApiTypes.BOOL),
        ],
        responses={200: AdminPropertyListSerializer(many=True)},
        tags=["Admin — Agents"],
    ),
)

AdminPropertyViewSetSchema = extend_schema_view(
    list=extend_schema(
        summary="List All Properties",
        description="""
Admin-only. Platform-wide property list with filtering.

Filters:
- `visible` — true/false
- `is_available` — true/false
- `property_listing` — RENT, FOR_SALE, SHORT_LET
- `search` — title, location, agent email
- `ordering` — created_at, price, title
        """,
        parameters=[
            OpenApiParameter("visible", OpenApiTypes.BOOL),
            OpenApiParameter("is_available", OpenApiTypes.BOOL),
            OpenApiParameter("property_listing", OpenApiTypes.STR),
            OpenApiParameter("search", OpenApiTypes.STR),
            OpenApiParameter("ordering", OpenApiTypes.STR),
        ],
        responses={200: AdminPropertyListSerializer(many=True)},
        tags=["Admin — Properties"],
    ),
    retrieve=extend_schema(
        summary="Get Property Detail",
        description="Admin-only. Full property detail including gallery images and amenities.",
        responses={200: AdminPropertyDetailSerializer()},
        tags=["Admin — Properties"],
    ),
    moderate=extend_schema(
        summary="Moderate Property",
        description="""
Admin-only. Toggle moderation flags on a property.

- `visible` — hide/show the listing platform-wide
- `is_available` — mark as unavailable
- `is_featured` — feature/unfeature on the homepage
        """,
        request=AdminPropertyModerationSerializer(),
        responses={200: AdminPropertyDetailSerializer()},
        tags=["Admin — Properties"],
    ),
)
