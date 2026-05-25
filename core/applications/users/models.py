from typing import ClassVar

import auto_prefetch
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db.models import CASCADE
from django.db.models import SET_NULL
from django.db.models import BooleanField
from django.db.models import CharField
from django.db.models import DateField
from django.db.models import DecimalField
from django.db.models import EmailField
from django.db.models import FileField
from django.db.models import ImageField
from django.db.models import JSONField
from django.db.models import PositiveIntegerField
from django.db.models import TextField
from django.db.models import URLField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from core.helpers.enums import AgentTypeChoices
from core.helpers.enums import AuthProviderChoices
from core.helpers.enums import GenderChoices
from core.helpers.enums import UserRoleChoice
from core.helpers.enums import VerificationStatusChoices
from core.helpers.media import MediaHelper
from core.helpers.models import UIDTimeBasedModel

from .managers import UserManager


class User(AbstractUser):
    """
    Custom user model for Real Estate Marketplace Africa.

    Authentication supports three flows:
      - Email + password
      - Phone + password
      - Google OAuth (social)

    ``email`` is nullable to support phone-only signup.
    ``phone_number`` lives here (not only on UserProfile) because it is
    used as an authentication credential, not merely a contact detail.

    Migration safety
    ----------------
    All new fields are nullable / have defaults so existing rows are unaffected.
    Fields that existed before are left untouched.
    """

    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]  # suppressed on AbstractUser
    last_name = None   # type: ignore[assignment]  # suppressed on AbstractUser

    first_name_field = CharField(
        _("First Name"),
        max_length=150,
        blank=True,
        null=True,
    )
    last_name_field = CharField(
        _("Last Name"),
        max_length=150,
        blank=True,
        null=True,
    )
    email = EmailField(
        _("email address"),
        blank=True,
        null=True,
        unique=True,
    )

    phone_number = CharField(
        _("Phone Number"),
        max_length=20,
        blank=True,
        null=True,
        unique=True,
    )

    username = None

    role = CharField(
        _("Role"),
        max_length=50,
        blank=True,
        null=True,
        choices=UserRoleChoice.choices,
    )

    auth_provider = CharField(
        _("Auth Provider"),
        max_length=20,
        choices=AuthProviderChoices.choices,
        default=AuthProviderChoices.EMAIL,
        blank=True,
        null=True,
    )

    is_email_verified = BooleanField(_("Email Verified"), default=False)
    is_phone_verified = BooleanField(_("Phone Verified"), default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects: ClassVar[UserManager] = UserManager()

    class Meta(AbstractUser.Meta):
        swappable = "AUTH_USER_MODEL"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def get_absolute_url(self) -> str:
        return reverse("users:detail", kwargs={"pk": self.id})

    def get_profile_url(self) -> str:
        """Return the profile URL based on the user's role."""
        if self.role == UserRoleChoice.AGENT.value:
            return reverse("users:agent_profile", kwargs={"pk": self.id})
        return reverse("users:user_profile", kwargs={"pk": self.id})

    get_profile_urls = get_profile_url  # type: ignore[assignment]

    def get_full_name(self) -> str:
        """
        Return the best available full name.

        Priority: first_name_field + last_name_field → name → email → phone
        """
        if self.first_name_field or self.last_name_field:
            return " ".join(
                filter(None, [self.first_name_field, self.last_name_field])
            ).strip()
        return self.name or self.email or self.phone_number or "Unknown User"

    def save(self, *args, **kwargs):
        """
        Keep the legacy ``name`` field in sync with first/last so that
        existing code that reads ``user.name`` continues to work.
        """
        if self.first_name_field or self.last_name_field:
            self.name = self.get_full_name()
        super().save(*args, **kwargs)


    @property
    def is_customer(self) -> bool:
        return self.role == UserRoleChoice.CUSTOMER.value

    @property
    def is_agent(self) -> bool:
        return self.role == UserRoleChoice.AGENT.value

    @property
    def agent_profile_or_none(self):
        """Return the AgentProfile if it exists, else None."""
        return getattr(self, "agent_profile", None)

    def __str__(self) -> str:
        return self.get_full_name()





class BaseProfile(UIDTimeBasedModel):
    """Abstract base for all profile types."""

    profile_picture = ImageField(
        upload_to=MediaHelper.get_image_upload_path,
        blank=True,
        null=True,
    )

    class Meta:
        abstract = True

    @property
    def get_profile_picture(self) -> str:
        """Return profile picture URL or the default avatar."""
        if self.profile_picture:
            return self.profile_picture.url
        return f"{settings.STATIC_URL}images/avatar.png"

    @property
    def full_name(self) -> str:
        """Return the full name of the associated user."""
        return self.user.get_full_name() if self.user else "Unknown User"



class UserProfile(BaseProfile):
    """
    Extended profile for Buyer / Renter accounts.

    ``phone_number`` is kept here as a denormalised copy of ``User.phone_number``
    for display purposes and to preserve backwards compatibility with any code
    that reads it directly from the profile.
    """

    user = auto_prefetch.OneToOneField(
        "users.User",
        on_delete=CASCADE,
        related_name="profile",
    )

    phone_number = CharField(
        _("Phone Number"),
        max_length=20,
        blank=True,
        null=True,
        help_text=_(
            "Denormalised copy of User.phone_number for display purposes."
        ),
    )

    # Saved search preferences
    preferred_location = CharField(max_length=255, blank=True, null=True)
    preferred_property_type = CharField(max_length=255, blank=True, null=True)
    min_budget = DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True
    )
    max_budget = DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True
    )
    preferred_features = JSONField(blank=True, null=True)
    address = TextField(blank=True, null=True)
    is_premium = BooleanField(default=False)

    class Meta(auto_prefetch.Model.Meta):
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"{self.user.get_full_name()}'s Profile"


# ---------------------------------------------------------------------------
# Social media links
# ---------------------------------------------------------------------------


class SocialMediaLinks(UIDTimeBasedModel):
    """Stores optional social media profile URLs for any user."""

    user = auto_prefetch.OneToOneField(
        "users.User",
        on_delete=CASCADE,
        related_name="social_media_links",
    )
    facebook = URLField(max_length=255, blank=True, null=True)
    twitter = URLField(max_length=255, blank=True, null=True)
    linkedin = URLField(max_length=255, blank=True, null=True)
    instagram = URLField(max_length=255, blank=True, null=True)

    class Meta(auto_prefetch.Model.Meta):
        verbose_name = "Social Media Links"
        verbose_name_plural = "Social Media Links"
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"{self.user.get_full_name()}'s Social Links"


# ---------------------------------------------------------------------------
# Agent profile
# ---------------------------------------------------------------------------


class AgentProfile(BaseProfile):
    """
    Extended profile for Agent / Landlord accounts.

    Includes verification workflow fields, subscription linkage, and
    office contact details.
    """

    user = auto_prefetch.OneToOneField(
        "users.User",
        on_delete=CASCADE,
        related_name="agent_profile",
    )
    gender = CharField(
        _("Gender"),
        max_length=20,
        choices=GenderChoices.choices,
        blank=True,
        null=True,
    )
    date_of_birth = DateField(
        _("Date of Birth"),
        blank=True,
        null=True,
    )

    # ------------------------------------------------------------------
    # Agent classification
    # ------------------------------------------------------------------
    agent_type = CharField(
        _("Agent Type"),
        max_length=50,
        choices=AgentTypeChoices.choices,
    )
    # ------------------------------------------------------------------
    # Business details
    # ------------------------------------------------------------------
    company_name = CharField(max_length=255, blank=True, null=True)
    company_registration_number = CharField(
        max_length=50, unique=True, blank=True, null=True
    )
    license_number = CharField(
        max_length=50, unique=True, blank=True, null=True
    )
    office_location = CharField(max_length=255, blank=True, null=True)
    office_phone_no = CharField(max_length=20, blank=True, null=True)
    office_address = CharField(max_length=255, blank=True, null=True)
    description = TextField(blank=True, null=True)

    # ------------------------------------------------------------------
    # Performance
    # ------------------------------------------------------------------
    rating = DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.0,
        blank=True,
        null=True,
    )

    # ------------------------------------------------------------------
    # Verification documents
    # ------------------------------------------------------------------
    license_document = FileField(
        upload_to=MediaHelper.get_image_upload_path,
        blank=True,
        null=True,
    )
    company_registration_document = FileField(
        upload_to=MediaHelper.get_image_upload_path,
        blank=True,
        null=True,
    )
    years_of_experience = PositiveIntegerField(
        _("Years of Experience"),
        blank=True,
        null=True,
    )
    verification_status = CharField(
        max_length=20,
        choices=VerificationStatusChoices.choices,
        default=VerificationStatusChoices.PENDING,
    )
    verified = BooleanField(default=False)

    # ------------------------------------------------------------------
    # Subscription
    # ------------------------------------------------------------------
    current_subscription = auto_prefetch.OneToOneField(
        "subscriptions.AgentSubscription",
        on_delete=SET_NULL,
        null=True,
        blank=True,
        related_name="active_for_agent",
    )

    class Meta(auto_prefetch.Model.Meta):
        verbose_name = "Agent Profile"
        verbose_name_plural = "Agent Profiles"
        ordering = ["-id"]

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def clean(self):
        """Enforce required fields for licensed real estate agents."""
        if self.agent_type == AgentTypeChoices.REAL_ESTATE_AGENT:
            errors = {}
            if not self.company_name:
                errors["company_name"] = _(
                    "Company name is required for real estate agents."
                )
            if not self.license_number:
                errors["license_number"] = _(
                    "License number is required for real estate agents."
                )
            if errors:
                raise ValidationError(errors)

    # ------------------------------------------------------------------
    # Subscription helpers
    # ------------------------------------------------------------------

    def has_active_subscription(self) -> bool:
        """Return True if the agent has a currently valid subscription."""
        return bool(
            self.current_subscription and self.current_subscription.is_valid()
        )

    def subscription_plan(self) -> str | None:
        """Return the current subscription plan name, or None."""
        return (
            self.current_subscription.plan if self.current_subscription else None
        )

    def days_left_in_subscription(self) -> int | None:
        """Return remaining days in the active subscription, or None."""
        if not self.current_subscription:
            return None
        return self.current_subscription.remaining_days()

    def set_current_subscription(self, subscription) -> None:
        """
        Assign or replace the active subscription.

        Raises ``ValidationError`` if the given subscription is already expired.
        """
        if subscription and not subscription.is_valid():
            raise ValidationError(
                _("Cannot assign an expired subscription.")
            )
        self.current_subscription = subscription
        self.save(update_fields=["current_subscription"])

    def __str__(self) -> str:
        return self.user.get_full_name()
