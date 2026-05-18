from __future__ import annotations

from rest_framework import serializers

from core.applications.property.models import Amenity
from core.applications.property.models import FavoriteProperty
from core.applications.property.models import Lead
from core.applications.property.models import Property
from core.applications.property.models import PropertyImage
from core.applications.property.models import PropertySubscription
from core.applications.property.models import PropertyViewing

# ---------------------------------------------------------------------------
# Shared mixin
# ---------------------------------------------------------------------------


class AbsoluteURLMixin:
    """
    Provides ``_absolute_url`` for serializers that need to build absolute
    media URLs.  Works with and without a request in context so management
    commands and tests without a RequestFactory don't explode.
    """

    def _absolute_url(self, path: str) -> str:
        request = self.context.get("request")
        return request.build_absolute_uri(path) if request else path



class AmenitySerializer(serializers.ModelSerializer):
    """
    Rendered in the "Features & Amenities" grid on the property detail page.
    Also returned by the amenity filter dropdown endpoint.
    """

    class Meta:
        model = Amenity
        fields = ("id", "name", "description")
        read_only_fields = fields


class PropertyImageSerializer(AbsoluteURLMixin, serializers.ModelSerializer):
    """
    One gallery image row.  ``url`` is built from the already-loaded
    ImageField — zero database hits.
    """

    url = serializers.SerializerMethodField()

    class Meta:
        model = PropertyImage
        fields = ("id", "url", "order")
        read_only_fields = fields

    def get_url(self, obj: PropertyImage) -> str:
        return self._absolute_url(obj.image.url) if obj.image else ""



class AgentSummarySerializer(AbsoluteURLMixin, serializers.Serializer):
    """
    Compact agent card shown on the property detail page and mobile cards.

    IMPORTANT: ``obj`` is an ``AgentProfile`` instance.
    ``agent__user`` and ``agent`` must be covered by select_related in the
    calling queryset (``with_card_relations()`` handles this).
    No method here may call the database.
    """

    id = serializers.CharField(source="pk")
    full_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    phone = serializers.CharField(source="phone_number", default="")
    email = serializers.SerializerMethodField()
    # ``properties`` is prefetched by with_card_relations() so .count()
    # resolves from the in-memory cache.
    total_listings = serializers.SerializerMethodField()

    def get_full_name(self, obj) -> str:
        """
        Builds the agent's full name from the related User record, falling
        back to email if no name is available.
        """
        user = getattr(obj, "user", None)
        if not user:
            return ""
        name = f"{user.first_name} {user.last_name}".strip()
        return name or user.email

    def get_email(self, obj) -> str:
        user = getattr(obj, "user", None)
        return user.email if user else ""

    def get_avatar_url(self, obj) -> str | None:
        """
        Builds the absolute URL for the agent's avatar, if set.
        """
        avatar = getattr(obj, "avatar", None)
        return self._absolute_url(avatar.url) if avatar else None

    def get_total_listings(self, obj) -> int:
        return obj.properties.count()




class PropertyCardSerializer(AbsoluteURLMixin, serializers.ModelSerializer):
    """
    Compact property card.  Used on:
      • Home page featured grid
      • Listing page grid (For Sale / For Rent / Short-let)
      • Similar properties strip on the detail page
      • Mobile property cards

    Contract: every field either reads a model column / @property directly,
    or reads from a pre-fetched / annotated cache.  Nothing here queries.

    ``is_favorited`` must be annotated by the queryset before serialization:
        PropertyQuerySet.with_favorite_annotation(user=request.user)
    """

    main_image_url = serializers.SerializerMethodField()
    price_display = serializers.CharField(read_only=True)
    price_suffix = serializers.CharField(read_only=True)
    availability_label = serializers.CharField(read_only=True)
    listing_type_display = serializers.CharField(
        source="get_property_listing_display", read_only=True
    )
    property_type_display = serializers.CharField(
        source="get_property_type_display", read_only=True
    )
    agent = AgentSummarySerializer(read_only=True)
    is_favorited = serializers.BooleanField(read_only=True, default=False)
    is_featured = serializers.BooleanField(read_only=True)

    class Meta:
        model = Property
        fields = (
            "id",
            "title",
            "slug",
            "location",
            "price",
            "price_display",
            "price_suffix",
            "property_type",
            "property_type_display",
            "property_listing",
            "listing_type_display",
            "bedrooms",
            "bathrooms",
            "sqft",
            "is_available",
            "availability_label",
            "is_featured",
            "is_favorited",
            "main_image_url",
            "agent",
            "created_at",
        )
        read_only_fields = fields

    def get_main_image_url(self, obj: Property) -> str:
        if obj.cover_image:
            return self._absolute_url(obj.cover_image.url)
        # obj.images.all() resolves from the prefetch cache when
        # with_card_relations() was called — no extra query.
        images = obj.images.all()
        if images:
            return self._absolute_url(images[0].image.url)
        return "/static/images/placeholder.jpg"




class PropertyDetailSerializer(AbsoluteURLMixin, serializers.ModelSerializer):
    """
    Full property detail page payload.

    Extends PropertyCardSerializer with:
      • Full description
      • All gallery images (ordered)
      • Full amenity list
      • Similar properties strip

    ``similar_properties`` is injected via ``context["similar_properties"]``
    (a pre-evaluated list) by the service layer — no query fires here.
    """

    main_image_url = serializers.SerializerMethodField()
    price_display = serializers.CharField(read_only=True)
    price_suffix = serializers.CharField(read_only=True)
    availability_label = serializers.CharField(read_only=True)
    listing_type_display = serializers.CharField(
        source="get_property_listing_display", read_only=True
    )
    property_type_display = serializers.CharField(
        source="get_property_type_display", read_only=True
    )
    agent = AgentSummarySerializer(read_only=True)
    images = PropertyImageSerializer(many=True, read_only=True)
    amenities = AmenitySerializer(many=True, read_only=True)
    is_featured = serializers.BooleanField(read_only=True)
    is_favorited = serializers.BooleanField(read_only=True, default=False)
    similar_properties = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = (
            "id",
            "title",
            "slug",
            "description",
            "location",
            "price",
            "price_display",
            "price_suffix",
            "property_type",
            "property_type_display",
            "property_listing",
            "listing_type_display",
            "bedrooms",
            "bathrooms",
            "sqft",
            "is_available",
            "availability_label",
            "is_featured",
            "is_favorited",
            "main_image_url",
            "images",
            "amenities",
            "agent",
            "similar_properties",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_main_image_url(self, obj: Property) -> str:
        if obj.cover_image:
            return self._absolute_url(obj.cover_image.url)
        images = obj.images.all()
        return self._absolute_url(images[0].image.url) if images else "/static/images/placeholder.jpg"

    def get_similar_properties(self, obj: Property) -> list:
        similar = self.context.get("similar_properties", [])
        return PropertyCardSerializer(similar, many=True, context=self.context).data





class PropertyWriteSerializer(serializers.ModelSerializer):
    """
    Validates agent listing payloads for create and update.

    ``agent`` is never accepted from the client — it is injected by the
    service layer from ``request.user.agent_profile``.

    ``amenity_ids`` is write-only; the service layer calls ``.set()`` on
    the M2M relation after the instance is saved.
    """

    amenity_ids = serializers.PrimaryKeyRelatedField(
        queryset=Amenity.objects.all(),
        many=True,
        write_only=True,
        source="amenities",
        required=False,
    )

    class Meta:
        model = Property
        fields = (
            "title",
            "description",
            "property_type",
            "property_listing",
            "price",
            "location",
            "bedrooms",
            "bathrooms",
            "sqft",
            "cover_image",
            "is_available",
            "amenity_ids",
        )





class CategorySummarySerializer(serializers.Serializer):
    """
    Powers the three category cards on the home page:
      For Sale | For Rent | Short Let

    Counts come from a single GROUP BY query in the service layer —
    this serializer only shapes the already-computed dict.
    """

    listing_type = serializers.CharField()
    label = serializers.CharField()
    count = serializers.IntegerField()
    icon = serializers.CharField()





class HomePageSerializer(serializers.Serializer):
    """
    Single response envelope — the home page needs only one API call.
    """

    featured_properties = PropertyCardSerializer(many=True)
    categories = CategorySummarySerializer(many=True)





class FavoriteToggleSerializer(serializers.Serializer):
    """
    Request:  { "property_id": "<uuid>" }
    Response: { "property_id": "<uuid>", "is_favorited": true|false,
                "message": "..." }
    """

    property_id = serializers.UUIDField()
    is_favorited = serializers.BooleanField(read_only=True)
    message = serializers.CharField(read_only=True)


class FavoritePropertySerializer(serializers.ModelSerializer):
    """
    Renders one row in the user's saved / favorites list.
    ``property`` reads from the prefetch cache set by
    ``FavoritePropertyQuerySet.with_property_card()``.
    """

    property = PropertyCardSerializer(read_only=True)

    class Meta:
        model = FavoriteProperty
        fields = ("id", "property", "created_at")
        read_only_fields = fields





class PropertySubscriptionSerializer(serializers.ModelSerializer):
    property_type_display = serializers.CharField(
        source="get_property_type_display", read_only=True
    )

    class Meta:
        model = PropertySubscription
        fields = (
            "id",
            "location",
            "property_type",
            "property_type_display",
            "created_at",
        )
        read_only_fields = ("id", "property_type_display", "created_at")

    def validate(self, attrs: dict) -> dict:
        user = self.context["request"].user
        qs = PropertySubscription.objects.filter(
            user=user,
            location=attrs.get("location"),
            property_type=attrs.get("property_type"),
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "You already have an alert for this location and property type."
            )
        return attrs





class ViewingCreateSerializer(serializers.Serializer):
    """
    Submitted from the "Schedule a Viewing" modal (mobile Image 5).
    ``property_id`` identifies the listing; ``lead_id`` is optional and
    links the viewing to an existing lead.
    Persistence is delegated to PropertyViewingService.create_viewing().
    """

    property_id = serializers.UUIDField()
    lead_id = serializers.UUIDField(required=False, allow_null=True)
    scheduled_time = serializers.DateTimeField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_scheduled_time(self, value):
        from django.utils import timezone as tz

        if value <= tz.now():
            raise serializers.ValidationError("Scheduled time must be in the future.")
        return value

    def validate(self, attrs: dict) -> dict:
        property_id = attrs["property_id"]
        lead_id = attrs.get("lead_id")

        if not Property.objects.filter(
            pk=property_id, visible=True, is_available=True
        ).exists():
            raise serializers.ValidationError(
                {"property_id": "Property not found or is no longer available."}
            )

        if lead_id:
            try:
                lead = Lead.objects.get(pk=lead_id)
            except Lead.DoesNotExist:
                raise serializers.ValidationError({"lead_id": "Lead not found."})
            if str(lead.property_link_id) != str(property_id):
                raise serializers.ValidationError(
                    {"lead_id": "This lead does not belong to the selected property."}
                )
            attrs["lead"] = lead

        return attrs


class ViewingSerializer(serializers.ModelSerializer):
    """
    Read representation of a viewing.
    Returned after creation and in the user's viewing history list.
    All source fields are covered by select_related in
    ``PropertyViewingQuerySet.with_relations()``.
    """

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    property_title = serializers.CharField(source="property.title", read_only=True)
    property_slug = serializers.CharField(source="property.slug", read_only=True)
    property_location = serializers.CharField(source="property.location", read_only=True)

    class Meta:
        model = PropertyViewing
        fields = (
            "id",
            "property_title",
            "property_slug",
            "property_location",
            "scheduled_time",
            "status",
            "status_display",
            "notes",
            "cancellation_reason",
            "created_at",
        )
        read_only_fields = fields


class ViewingCancelSerializer(serializers.Serializer):
    """Request body for PATCH /viewings/{id}/cancel/"""

    cancellation_reason = serializers.CharField(
        required=False, allow_blank=True, default=""
    )




class LeadCreateSerializer(serializers.Serializer):
    """
    Submitted when a user taps "Contact Agent" on the mobile card.
    ``agent`` and ``user`` are resolved by LeadService — never client-supplied.
    """

    property_id = serializers.UUIDField()
    message = serializers.CharField(
        max_length=2000, required=False, allow_blank=True, default=""
    )

    def validate_property_id(self, value):
        if not Property.objects.filter(
            pk=value, visible=True, is_available=True
        ).exists():
            raise serializers.ValidationError(
                "Property not found or is no longer available."
            )
        return value


class LeadSerializer(serializers.ModelSerializer):
    """
    Full lead payload — returned after "Contact Agent" and used in the
    agent CRM dashboard.

    ``upcoming_viewing`` reads from ``upcoming_viewings_cache`` (the
    Prefetch ``to_attr`` set by LeadQuerySet.with_relations()) when
    available, and falls back to the model property for single-object
    responses (e.g. after create).  Either path is query-free.
    """

    property = PropertyCardSerializer(source="property_link", read_only=True)
    upcoming_viewing = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_full_name = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = (
            "id",
            "property",
            "user_email",
            "user_full_name",
            "message",
            "notes",
            "status",
            "status_display",
            "last_contact",
            "upcoming_viewing",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "property",
            "user_email",
            "user_full_name",
            "status_display",
            "last_contact",
            "upcoming_viewing",
            "created_at",
            "updated_at",
        )

    def get_user_full_name(self, obj: Lead) -> str:
        u = obj.user
        return f"{u.first_name} {u.last_name}".strip() or u.email

    def get_upcoming_viewing(self, obj: Lead) -> dict | None:
        # Prefer the prefetch cache (list) set by LeadQuerySet.with_relations().
        cache = getattr(obj, "upcoming_viewings_cache", None)
        viewing = cache[0] if cache else obj.upcoming_viewing
        if viewing is None:
            return None
        return ViewingSerializer(viewing, context=self.context).data


class LeadStatusUpdateSerializer(serializers.Serializer):
    """
    Allows an agent to advance a lead's status.
    Choices are bound at runtime to stay in sync with the enum.
    """

    status = serializers.ChoiceField(choices=[])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from core.helpers.enums import Lead_Status_Choices
        self.fields["status"].choices = Lead_Status_Choices.choices
