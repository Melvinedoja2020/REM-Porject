from rest_framework import serializers

from core.applications.property.models import Property
from core.applications.property.models import PropertyImage
from core.applications.users.models import AgentProfile
from core.helpers.enums import VerificationStatusChoices


class AdminAgentListSerializer(serializers.ModelSerializer):
    """
    Compact agent row for the admin agent management table.
    """
    full_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    total_listings = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = AgentProfile
        fields = (
            "id",
            "full_name",
            "email",
            "phone_number",
            "profile_picture",
            "agent_type",
            "company_name",
            "office_location",
            "rating",
            "years_of_experience",
            "verified",
            "verification_status",
            "total_listings",
            "created_at",
        )

    def get_full_name(self, obj) -> str:
        return obj.user.get_full_name()

    def get_email(self, obj) -> str:
        return obj.user.email or ""

    def get_phone_number(self, obj) -> str:
        return obj.user.phone_number or ""

    def get_profile_picture(self, obj) -> str:
        return obj.get_profile_picture

    def get_total_listings(self, obj) -> int:
        return obj.properties.count()


class AdminAgentDetailSerializer(AdminAgentListSerializer):
    """
    Full agent detail for the admin agent detail/review page.
    Includes sensitive fields only admins should see.
    """

    class Meta(AdminAgentListSerializer.Meta):
        fields = AdminAgentListSerializer.Meta.fields + (
            "gender",
            "date_of_birth",
            "company_registration_number",
            "license_number",
            "office_phone_no",
            "office_address",
            "description",
            "license_document",
            "company_registration_document",
        )


class AdminAgentVerificationSerializer(serializers.ModelSerializer):
    """
    Used by admin to approve, decline, or revoke agent verification.
    Only exposes the two fields that change during a verification action.
    """
    verification_status = serializers.ChoiceField(
        choices=VerificationStatusChoices.choices,
    )
    rejection_reason = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="Required when declining verification.",
    )

    class Meta:
        model = AgentProfile
        fields = ("verification_status", "rejection_reason")

    def validate(self, attrs):
        status = attrs.get("verification_status")
        reason = attrs.get("rejection_reason", "")
        if status == VerificationStatusChoices.REJECTED and not reason:
            raise serializers.ValidationError(
                {"rejection_reason": "A reason is required when declining verification."}
            )
        return attrs


class AdminPropertyImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyImage
        fields = ("id", "image", "order", "created_at")


class AdminPropertyListSerializer(serializers.ModelSerializer):
    """
    Compact property row for the admin property management table.
    """
    agent_name = serializers.SerializerMethodField()
    agent_id = serializers.CharField(source="agent.pk", read_only=True)
    main_image_url = serializers.CharField(read_only=True)

    class Meta:
        model = Property
        fields = (
            "id",
            "slug",
            "title",
            "agent_id",
            "agent_name",
            "property_type",
            "property_listing",
            "price",
            "location",
            "bedrooms",
            "bathrooms",
            "sqft",
            "is_available",
            "is_featured",
            "visible",
            "main_image_url",
            "created_at",
        )

    def get_agent_name(self, obj) -> str:
        return obj.agent.user.get_full_name()


class AdminPropertyDetailSerializer(AdminPropertyListSerializer):
    """
    Full property detail for admin review.
    """
    images = AdminPropertyImageSerializer(many=True, read_only=True)
    amenities = serializers.StringRelatedField(many=True, read_only=True)

    class Meta(AdminPropertyListSerializer.Meta):
        fields = AdminPropertyListSerializer.Meta.fields + (
            "description",
            "cover_image",
            "images",
            "amenities",
            "updated_at",
        )


class AdminPropertyModerationSerializer(serializers.ModelSerializer):
    """
    Allows admin to toggle visibility or availability of a property.
    Intentionally narrow — only exposes fields safe for moderation.
    """
    class Meta:
        model = Property
        fields = ("visible", "is_available", "is_featured")
