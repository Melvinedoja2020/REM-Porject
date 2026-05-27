from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import CreateModelMixin
from rest_framework.mixins import DestroyModelMixin
from rest_framework.mixins import ListModelMixin
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.parsers import FormParser
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework.viewsets import ModelViewSet
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.viewsets import ViewSet

from core.applications.property import services
from core.applications.property.api.schema.home_schema import HomePageViewSchema
from core.applications.property.api.schema.property_schemas import PropertyViewSetSchema
from core.applications.property.api.serializers import AgentSummarySerializer, AmenitySerializer
from core.applications.property.api.serializers import FavoritePropertySerializer
from core.applications.property.api.serializers import FavoriteToggleSerializer
from core.applications.property.api.serializers import HomePageSerializer
from core.applications.property.api.serializers import LeadCreateSerializer
from core.applications.property.api.serializers import LeadSerializer
from core.applications.property.api.serializers import LeadStatusUpdateSerializer
from core.applications.property.api.serializers import PropertyCardSerializer
from core.applications.property.api.serializers import PropertyDetailSerializer
from core.applications.property.api.serializers import PropertySubscriptionSerializer
from core.applications.property.api.serializers import PropertyWriteSerializer
from core.applications.property.api.serializers import ViewingCancelSerializer
from core.applications.property.api.serializers import ViewingCreateSerializer
from core.applications.property.api.serializers import ViewingSerializer
from core.applications.property.models import Property
from core.applications.property.models import PropertySubscription
from core.applications.property.models import PropertyViewing
from core.applications.property.permissions import IsAgentUser
from core.applications.property.permissions import IsLeadOwnerOrPropertyAgent
from core.applications.property.permissions import IsLeadPropertyAgent
from core.applications.property.permissions import IsObjectOwner
from core.applications.property.permissions import IsPropertyOwnerAgent
from core.applications.property.permissions import IsVerifiedAgent
from core.applications.property.permissions import IsViewingOwnerOrPropertyAgent


def _ctx(request: Request) -> dict:
    """
    Builds the standard serializer context.
    Every serializer must receive this so AbsoluteURLMixin can construct
    correct absolute media URLs and so DRF's HyperlinkedRelatedField works.
    """
    return {"request": request}


def _agent_or_403(request: Request):
    """
    Returns the AgentProfile attached to the requesting user.
    Raises PermissionDenied when no profile exists.

    Used inside extra actions where the action-level permission class
    (IsAgentUser) has already been checked but the profile object is
    still needed to call a service function.
    """
    profile = getattr(request.user, "agent_profile", None)
    if not profile:
        raise PermissionDenied("An agent profile is required for this action.")
    return profile


def _parse_bool(value: str | None) -> bool | None:
    """
    Converts ?is_available=true|false query param to Python bool or None.
    Accepts: true / 1 / yes  →  True
             false / 0 / no  →  False
             absent / other  →  None
    """
    if value is None:
        return None
    return value.lower() in ("true", "1", "yes")



@HomePageViewSchema
class HomePageView(ViewSet):
    """
    GET /
    Aggregates featured properties + category cards in one network call.
    Fully public — no authentication required.
    """

    permission_classes = [AllowAny]

    def list(self, request: Request) -> Response:
        user = request.user if request.user.is_authenticated else None
        data = services.get_home_page_data(user=user)
        serializer = HomePageSerializer(data, context=_ctx(request))
        return Response(serializer.data)


class AgentPropertyListView(ListModelMixin, GenericViewSet):
    """
    GET /properties/agent/
    Returns the authenticated agent's listings annotated with
    lead_count and viewing_count for the agent dashboard table.
    """

    permission_classes = [IsAgentUser]
    serializer_class = PropertyCardSerializer

    def get_queryset(self):
        return services.get_agent_properties(
            agent=self.request.user.agent_profile,
            user=self.request.user,
        )

    def get_serializer_context(self):
        return {**super().get_serializer_context(), **_ctx(self.request)}





@PropertyViewSetSchema
class PropertyViewSet(ModelViewSet):
    """
    CRUD operations on Property, plus listing and extra actions.

    """
    parser_classes = [MultiPartParser, FormParser]
    lookup_field = "slug"

    permission_classes_by_action = {
        "list": [AllowAny],
        "retrieve": [AllowAny],
        "similar": [AllowAny],
        "create": [IsVerifiedAgent],
        "update": [IsPropertyOwnerAgent],
        "partial_update": [IsPropertyOwnerAgent],
        "destroy": [IsPropertyOwnerAgent],
        "agent_info": [IsAuthenticated],
    }

    serializer_class_by_action = {
        "list": PropertyCardSerializer,
        "similar": PropertyCardSerializer,
        "retrieve": PropertyDetailSerializer,
        "create": PropertyWriteSerializer,
        "update": PropertyWriteSerializer,
        "partial_update": PropertyWriteSerializer,
        "agent_info": AgentSummarySerializer,
    }


    def get_permissions(self):
        """
        Resolve permissions based on action using a mapping.
        Defaults to IsAuthenticated if action is not explicitly defined.
        """
        permission_classes = self.permission_classes_by_action.get(
            self.action,
            [IsAuthenticated],
        )
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        """
        Resolve serializer class dynamically based on action.
        Falls back to PropertyCardSerializer.
        """
        return self.serializer_class_by_action.get(
            self.action,
            PropertyCardSerializer,
        )

    def get_serializer_context(self):
        """Extend serializer context with request-scoped helpers."""
        return {
            **super().get_serializer_context(),
            **_ctx(self.request),
        }

    def get_queryset(self):
        """
        Returns filtered queryset for list endpoints.

        Notes
        -----
        - `retrieve` does not rely on queryset (handled manually).
        - Business logic delegated to service layer.
        """
        if self.action == "retrieve":
            return Property.objects.none()

        request = self.request
        user = request.user if request.user.is_authenticated else None
        params = request.query_params

        amenity_ids = [
            a.strip()
            for a in params.get("amenities", "").split(",")
            if a.strip()
        ]

        return services.get_property_list(
            user=user,
            listing_type=params.get("listing_type"),
            property_type=params.get("property_type"),
            location=params.get("location"),
            min_price=params.get("min_price"),
            max_price=params.get("max_price"),
            min_bedrooms=params.get("min_bedrooms"),
            max_bedrooms=params.get("max_bedrooms"),
            min_bathrooms=params.get("min_bathrooms"),
            amenity_ids=amenity_ids or None,
            is_available=_parse_bool(params.get("is_available")),
            search=params.get("search"),
            ordering=params.get("ordering", "-created_at"),
        )

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------

    def list(self, request: Request, *args, **kwargs) -> Response:
        """Paginated property card list."""
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)

        serializer = self.get_serializer(
            page if page is not None else queryset,
            many=True,
        )

        if page is not None:
            return self.get_paginated_response(serializer.data)

        return Response(serializer.data)

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        """
        Retrieve a property with pre-fetched similar properties.
        """
        user = request.user if request.user.is_authenticated else None

        prop, similar = services.get_property_detail(
            slug=kwargs["slug"],
            user=user,
        )

        self.check_object_permissions(request, prop)

        serializer = self.get_serializer(
            prop,
            context={
                **self.get_serializer_context(),
                "similar_properties": similar,
            },
        )

        return Response(serializer.data)

    def create(self, request: Request, *args, **kwargs) -> Response:
        """Create a new property listing."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        prop = services.create_property(
            agent=request.user.agent_profile,
            validated_data=dict(serializer.validated_data),
        )

        output = PropertyDetailSerializer(
            prop,
            context=self.get_serializer_context(),
        )

        return Response(output.data, status=status.HTTP_201_CREATED)

    def update(self, request: Request, *args, **kwargs) -> Response:
        """Update a property (PUT/PATCH)."""
        partial = kwargs.pop("partial", False)
        instance = self._get_owned_property()

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial,
        )
        serializer.is_valid(raise_exception=True)

        prop = services.update_property(
            instance=instance,
            agent=request.user.agent_profile,
            validated_data=dict(serializer.validated_data),
        )

        output = PropertyDetailSerializer(
            prop,
            context=self.get_serializer_context(),
        )

        return Response(output.data)

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        """Delete a property."""
        instance = self._get_owned_property()

        services.delete_property(
            instance=instance,
            agent=request.user.agent_profile,
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    # ------------------------------------------------------------------
    # Extra actions
    # ------------------------------------------------------------------

    @action(detail=True, methods=["get"])
    def similar(self, request: Request, slug=None) -> Response:
        """Return similar properties."""
        user = request.user if request.user.is_authenticated else None

        _, similar = services.get_property_detail(slug=slug, user=user)

        serializer = self.get_serializer(similar, many=True)
        return Response(serializer.data)

    @action(
        detail=True, methods=["get"],
        url_path="agent", permission_classes=[IsAuthenticated]
    )
    def agent_info(self, request: Request, slug=None) -> Response:
        """Return the agent profile for the agent who listed this property."""
        prop = get_object_or_404(
            Property.objects.visible().select_related(
                "agent",
                "agent__user",
            ).prefetch_related("agent__properties"),
            slug=slug,
        )
        serializer = AgentSummarySerializer(
            prop.agent,
            context=self.get_serializer_context(),
        )
        return Response(serializer.data)
    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_owned_property(self) -> Property:
        """
        Fetch property and enforce ownership permission.
        """
        obj = get_object_or_404(
            Property.objects.visible(),
            slug=self.kwargs["slug"],
        )
        self.check_object_permissions(self.request, obj)
        return obj


# ---------------------------------------------------------------------------
# Amenity ViewSet  (read-only)
# ---------------------------------------------------------------------------


class AmenityViewSet(ReadOnlyModelViewSet):
    """
    GET /amenities/       Amenity list — drives the listing-page filter checkboxes.
    GET /amenities/<pk>/  Amenity detail.
    Fully public — no authentication required.
    """

    permission_classes = [AllowAny]
    serializer_class = AmenitySerializer

    def get_queryset(self):
        return services.get_all_amenities()


# ---------------------------------------------------------------------------
# Lead ViewSet
# ---------------------------------------------------------------------------


class LeadViewSet(
    CreateModelMixin,
    RetrieveModelMixin,
    ListModelMixin,
    GenericViewSet,
):
    """
    Leads are permanent enquiry records — no update or destroy.
    Status is advanced via the ``update_status`` extra action.

    get_permissions() breakdown
    ---------------------------
      create                →  IsAuthenticated          (any auth user)
      list                  →  IsAuthenticated          (own leads only — queryset-scoped)
      retrieve              →  IsLeadOwnerOrPropertyAgent
      agent_leads           →  IsAgentUser              (any agent)
      update_status         →  IsLeadPropertyAgent      (owning agent only)
    """

    def get_permissions(self):
        if self.action in ("list", "create"):
            return [IsAuthenticated()]
        if self.action == "retrieve":
            return [IsLeadOwnerOrPropertyAgent()]
        if self.action == "agent_leads":
            return [IsAgentUser()]
        if self.action == "update_status":
            return [IsLeadPropertyAgent()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "create":
            return LeadCreateSerializer
        if self.action == "update_status":
            return LeadStatusUpdateSerializer
        return LeadSerializer

    def get_serializer_context(self):
        return {**super().get_serializer_context(), **_ctx(self.request)}

    def get_queryset(self):
        """
        Default queryset scoped to the requesting user's own leads.
        The ``agent_leads`` extra action uses its own service call.
        """
        return services.get_user_leads(user=self.request.user)

    def get_object(self):
        """
        Fetches a Lead by PK with full relations pre-fetched, then runs
        the object-level permission check for the current action.
        """
        lead = services.get_lead(
            user=self.request.user,
            lead_id=self.kwargs["pk"],
        )
        self.check_object_permissions(self.request, lead)
        return lead

    # ------------------------------------------------------------------
    # Standard actions
    # ------------------------------------------------------------------

    def create(self, request: Request, *args, **kwargs) -> Response:
        """
        POST /leads/
        Idempotent — returns the existing lead (HTTP 200) when this
        (user, property) pair already has a lead.  New leads return HTTP 201.
        """
        serializer = LeadCreateSerializer(
            data=request.data, context=_ctx(request)
        )
        serializer.is_valid(raise_exception=True)
        lead = services.create_lead(
            user=request.user,
            property_id=serializer.validated_data["property_id"],
            message=serializer.validated_data.get("message", ""),
        )
        out = LeadSerializer(lead, context=_ctx(request))
        response_status = (
            status.HTTP_200_OK
            if getattr(lead, "_existed", False)
            else status.HTTP_201_CREATED
        )
        return Response(out.data, status=response_status)

    def list(self, request: Request, *args, **kwargs) -> Response:
        """GET /leads/ — authenticated user's own enquiry history."""
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = LeadSerializer(page, many=True, context=_ctx(request))
            return self.get_paginated_response(serializer.data)
        serializer = LeadSerializer(queryset, many=True, context=_ctx(request))
        return Response(serializer.data)

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        """GET /leads/<pk>/ — lead owner or property agent."""
        lead = self.get_object()
        serializer = LeadSerializer(lead, context=_ctx(request))
        return Response(serializer.data)

    # ------------------------------------------------------------------
    # Extra actions
    # ------------------------------------------------------------------

    @action(detail=False, methods=["get"], url_path="agent_leads")
    def agent_leads(self, request: Request) -> Response:
        """
        GET /leads/agent_leads/
        Agent CRM pipeline — all leads on the agent's listings.
        Optional ?status= filter for pipeline column views.
        Permission: IsAgentUser (see get_permissions).
        """
        agent = _agent_or_403(request)
        queryset = services.get_agent_leads(
            agent=agent,
            status=request.query_params.get("status"),
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = LeadSerializer(page, many=True, context=_ctx(request))
            return self.get_paginated_response(serializer.data)
        serializer = LeadSerializer(queryset, many=True, context=_ctx(request))
        return Response(serializer.data)

    @action(detail=True, methods=["patch"], url_path="status")
    def update_status(self, request: Request, pk=None) -> Response:
        """
        PATCH /leads/<pk>/status/
        Advances the lead's pipeline status.
        Permission: IsLeadPropertyAgent (see get_permissions) — only the
        property's agent, not just any agent.
        """
        lead = self.get_object()
        serializer = LeadStatusUpdateSerializer(
            data=request.data, context=_ctx(request)
        )
        serializer.is_valid(raise_exception=True)
        updated = services.update_lead_status(
            agent=request.user.agent_profile,
            lead_id=lead.pk,
            status=serializer.validated_data["status"],
        )
        out = LeadSerializer(updated, context=_ctx(request))
        return Response(out.data)


# ---------------------------------------------------------------------------
# PropertyViewing ViewSet
# ---------------------------------------------------------------------------


class PropertyViewingViewSet(
    CreateModelMixin,
    RetrieveModelMixin,
    ListModelMixin,
    GenericViewSet,
):
    """
    Viewings are soft-cancelled (status → CANCELLED) to preserve audit trail.

    get_permissions() breakdown
    ---------------------------
      create / list   →  IsAuthenticated              (any auth user)
      retrieve        →  IsViewingOwnerOrPropertyAgent
      cancel          →  IsViewingOwnerOrPropertyAgent
    """

    def get_permissions(self):
        if self.action in ("create", "list"):
            return [IsAuthenticated()]
        # retrieve and cancel
        return [IsViewingOwnerOrPropertyAgent()]

    def get_serializer_class(self):
        if self.action == "create":
            return ViewingCreateSerializer
        if self.action == "cancel":
            return ViewingCancelSerializer
        return ViewingSerializer

    def get_serializer_context(self):
        return {**super().get_serializer_context(), **_ctx(self.request)}

    def get_queryset(self):
        return services.get_user_viewings(user=self.request.user)

    def get_object(self):
        """
        Fetches a PropertyViewing by PK with all relations pre-fetched,
        then runs the object-level permission check.
        """
        obj = get_object_or_404(
            PropertyViewing.objects.with_relations(),
            pk=self.kwargs["pk"],
        )
        self.check_object_permissions(self.request, obj)
        return obj

    # ------------------------------------------------------------------
    # Standard actions
    # ------------------------------------------------------------------

    def create(self, request: Request, *args, **kwargs) -> Response:
        """POST /viewings/ — Schedule a Viewing modal (mobile)."""
        serializer = ViewingCreateSerializer(
            data=request.data, context=_ctx(request)
        )
        serializer.is_valid(raise_exception=True)
        viewing = services.create_viewing(
            user=request.user,
            validated_data=dict(serializer.validated_data),
        )
        out = ViewingSerializer(viewing, context=_ctx(request))
        return Response(out.data, status=status.HTTP_201_CREATED)

    def list(self, request: Request, *args, **kwargs) -> Response:
        """GET /viewings/ — authenticated user's viewing history."""
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ViewingSerializer(page, many=True, context=_ctx(request))
            return self.get_paginated_response(serializer.data)
        serializer = ViewingSerializer(queryset, many=True, context=_ctx(request))
        return Response(serializer.data)

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        """GET /viewings/<pk>/ — booking user or property agent."""
        viewing = self.get_object()
        serializer = ViewingSerializer(viewing, context=_ctx(request))
        return Response(serializer.data)

    # ------------------------------------------------------------------
    # Extra actions
    # ------------------------------------------------------------------

    @action(detail=True, methods=["patch"], url_path="cancel")
    def cancel(self, request: Request, pk=None) -> Response:
        """
        PATCH /viewings/<pk>/cancel/
        Soft-cancels a viewing.  Permission: IsViewingOwnerOrPropertyAgent
        (see get_permissions) — booking user or property's agent only.
        """
        viewing = self.get_object()
        serializer = ViewingCancelSerializer(
            data=request.data, context=_ctx(request)
        )
        serializer.is_valid(raise_exception=True)
        updated = services.cancel_viewing(
            user=request.user,
            viewing_id=viewing.pk,
            reason=serializer.validated_data.get("cancellation_reason", ""),
        )
        out = ViewingSerializer(updated, context=_ctx(request))
        return Response(out.data)


# ---------------------------------------------------------------------------
# FavoriteProperty ViewSet
# ---------------------------------------------------------------------------


class FavoritePropertyViewSet(ListModelMixin, GenericViewSet):
    """
    Favorites are managed via an idempotent toggle — the client never needs
    to track a FavoriteProperty PK.

    get_permissions() breakdown
    ---------------------------
      list    →  IsAuthenticated  (own favorites only — queryset-scoped)
      toggle  →  IsAuthenticated  (any auth user)
    """

    serializer_class = FavoritePropertySerializer

    def get_permissions(self):
        return [IsAuthenticated()]

    def get_queryset(self):
        return services.get_user_favorites(user=self.request.user)

    def get_serializer_context(self):
        return {**super().get_serializer_context(), **_ctx(self.request)}

    def list(self, request: Request, *args, **kwargs) -> Response:
        """GET /favorites/ — the authenticated user's saved properties."""
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = FavoritePropertySerializer(
                page, many=True, context=_ctx(request)
            )
            return self.get_paginated_response(serializer.data)
        serializer = FavoritePropertySerializer(
            queryset, many=True, context=_ctx(request)
        )
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="toggle")
    def toggle(self, request: Request) -> Response:
        """
        POST /favorites/toggle/
        Body: { "property_id": "<uuid>" }
        Idempotent — safe to call multiple times.
        """
        serializer = FavoriteToggleSerializer(
            data=request.data, context=_ctx(request)
        )
        serializer.is_valid(raise_exception=True)
        result = services.toggle_favorite(
            user=request.user,
            property_id=serializer.validated_data["property_id"],
        )
        out = FavoriteToggleSerializer(result, context=_ctx(request))
        return Response(out.data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# PropertySubscription ViewSet
# ---------------------------------------------------------------------------


class PropertySubscriptionViewSet(
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    GenericViewSet,
):
    """
    New-listing alert subscriptions.  No update — delete and recreate.

    get_permissions() breakdown
    ---------------------------
      list / create  →  IsAuthenticated (any auth user)
      destroy        →  IsObjectOwner   (own record only)
    """

    serializer_class = PropertySubscriptionSerializer

    def get_permissions(self):
        if self.action == "destroy":
            return [IsObjectOwner()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return services.get_user_subscriptions(user=self.request.user)

    def get_object(self):
        obj = get_object_or_404(
            PropertySubscription.objects.for_user(self.request.user),
            pk=self.kwargs["pk"],
        )
        self.check_object_permissions(self.request, obj)
        return obj

    def get_serializer_context(self):
        return {**super().get_serializer_context(), **_ctx(self.request)}

    def create(self, request: Request, *args, **kwargs) -> Response:
        """POST /subscriptions/"""
        serializer = PropertySubscriptionSerializer(
            data=request.data, context=_ctx(request)
        )
        serializer.is_valid(raise_exception=True)
        sub = services.create_subscription(
            user=request.user,
            validated_data=dict(serializer.validated_data),
        )
        out = PropertySubscriptionSerializer(sub, context=_ctx(request))
        return Response(out.data, status=status.HTTP_201_CREATED)

    def list(self, request: Request, *args, **kwargs) -> Response:
        """GET /subscriptions/"""
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = PropertySubscriptionSerializer(
                page, many=True, context=_ctx(request)
            )
            return self.get_paginated_response(serializer.data)
        serializer = PropertySubscriptionSerializer(
            queryset, many=True, context=_ctx(request)
        )
        return Response(serializer.data)

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        """DELETE /subscriptions/<pk>/"""
        services.delete_subscription(
            user=request.user,
            subscription_id=kwargs["pk"],
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
