from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.utils import OpenApiTypes
from drf_spectacular.utils import extend_schema
from drf_spectacular.utils import extend_schema_view

from core.applications.property.api.serializers import AgentSummarySerializer
from core.applications.property.api.serializers import PropertyCardSerializer
from core.applications.property.api.serializers import PropertyDetailSerializer
from core.applications.property.api.serializers import PropertyWriteSerializer

PropertyViewSetSchema = extend_schema_view(
    # ------------------------------------------------------------------
    # LIST
    # ------------------------------------------------------------------
    list=extend_schema(
        summary="List Properties",
        description="""
Retrieve a paginated list of publicly available properties.

This endpoint powers:
- Property listing page (Buy / Rent / Short-let)
- Homepage featured sections
- Mobile property grids

Supports extensive filtering, search, and ordering.
        """,
        parameters=[
            OpenApiParameter("listing_type", OpenApiTypes.STR, description="Sale, Rent, Short-let"),
            OpenApiParameter("property_type", OpenApiTypes.STR, description="Apartment, Duplex, etc."),
            OpenApiParameter("location", OpenApiTypes.STR),
            OpenApiParameter("min_price", OpenApiTypes.NUMBER),
            OpenApiParameter("max_price", OpenApiTypes.NUMBER),
            OpenApiParameter("min_bedrooms", OpenApiTypes.INT),
            OpenApiParameter("max_bedrooms", OpenApiTypes.INT),
            OpenApiParameter("min_bathrooms", OpenApiTypes.INT),
            OpenApiParameter("amenities", OpenApiTypes.STR, description="Comma-separated IDs"),
            OpenApiParameter("is_available", OpenApiTypes.BOOL),
            OpenApiParameter("search", OpenApiTypes.STR),
            OpenApiParameter("ordering", OpenApiTypes.STR),
        ],
        responses={200: PropertyCardSerializer(many=True)},
        tags=["Properties"],
    ),

    # ------------------------------------------------------------------
    # RETRIEVE
    # ------------------------------------------------------------------
    retrieve=extend_schema(
        summary="Retrieve Property Detail",
        description="""
Retrieve full details of a property using its slug.

Includes:
- Full property data
- Gallery images
- Amenities
- Agent info
- Similar properties (pre-fetched, no extra query)
        """,
        responses={200: PropertyDetailSerializer()},
        tags=["Properties"],
    ),

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------
    create=extend_schema(
        summary="Create Property",
        description="""
Create a new property listing.

- Only accessible to agent users
- Agent is inferred from authenticated user
- Returns full property detail after creation
        """,
        request={"multipart/form-data": PropertyWriteSerializer()},
        responses={201: PropertyDetailSerializer()},
        tags=["Properties"],
    ),

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------
    update=extend_schema(
        summary="Update Property",
        description="""
Fully update a property.

- Only the owning agent can update
        """,
        request={"multipart/form-data": PropertyWriteSerializer()},
        responses={200: PropertyDetailSerializer()},
        tags=["Properties"],
    ),

    # ------------------------------------------------------------------
    # PARTIAL UPDATE
    # ------------------------------------------------------------------
    partial_update=extend_schema(
        summary="Partially Update Property",
        description="""
Partially update a property.

- Only the owning agent can update
        """,
        request={"multipart/form-data": PropertyWriteSerializer()},
        responses={200: PropertyDetailSerializer()},
        tags=["Properties"],
    ),

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------
    destroy=extend_schema(
        summary="Delete Property",
        description="""
Delete a property listing.

- Only the owning agent can delete
        """,
        responses={204: None},
        tags=["Properties"],
    ),

    # ------------------------------------------------------------------
    # CUSTOM ACTION: SIMILAR
    # ------------------------------------------------------------------
    similar=extend_schema(
        summary="Get Similar Properties",
        description="""
Retrieve similar properties based on:
- Listing type
- Property type

Used for:
- "You may also like" section
- Recommendation strips
        """,
        responses={200: PropertyCardSerializer(many=True)},
        tags=["Properties"],
    ),

    # ------------------------------------------------------------------
    # CUSTOM ACTION: AGENT INFO
    # ------------------------------------------------------------------
    agent_info=extend_schema(
        summary="Get Property Agent",
        description="""
Retrieve the profile of the agent who listed a specific property.

- Requires authentication
- Returns compact agent card with contact details and trust signals
- Used on the property detail page to surface agent information

Includes:
- Full name and avatar
- Contact details (email, phone)
- Agent type and company name
- Verification status and rating
- Total active listings count
        """,
        responses={200: AgentSummarySerializer()},
        tags=["Properties"],
    ),
)
