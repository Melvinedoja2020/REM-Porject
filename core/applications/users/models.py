from typing import ClassVar

import auto_prefetch
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db.models import CASCADE
from django.db.models import BooleanField
from django.db.models import CharField
from django.db.models import DecimalField
from django.db.models import EmailField
from django.db.models import FileField
from django.db.models import ImageField
from django.db.models import JSONField
from django.db.models import TextField, SET_NULL
from django.db.models import URLField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from core.helper.enums import AgentTypeChoices
from core.helper.enums import UserRoleChoice
from core.helper.enums import VerificationStatusChoices
from core.helper.media import MediaHelper
from core.helper.models import UIDTimeBasedModel

from .managers import UserManager


class User(AbstractUser):
    """
    Default custom user model for real estate market place.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    email = EmailField(_("email address"), unique=True)
    username = None  # type: ignore[assignment]
    role = CharField(
        _("Role"),
        max_length=50,
        blank=True,
        null=True,
        choices=UserRoleChoice.choices,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects: ClassVar[UserManager] = UserManager()

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"pk": self.id})

    def get_profile_urls(self) -> str:
        """Returns the profile URL based on user type"""
        if self.role == UserRoleChoice.AGENT.value:
            return reverse("users:agent_profile", kwargs={"pk": self.id})
        # elif self.role == UserRoleChoice.REAL_ESTATE_OWNER.value:
        #     return reverse("users:real_estate_owner_profile", kwargs={"pk": self.id})
        return reverse("users:user_profile", kwargs={"pk": self.id})

    @property
    def is_customer(self) -> bool:
        return self.role == UserRoleChoice.CUSTOMER.value

    @property
    def is_agent(self) -> bool:
        return self.role == UserRoleChoice.AGENT.value

    @property
    def agent_profile_or_none(self):
        """Return the agent profile if it exists, else None."""
        return getattr(self, "agent_profile", None)


class BaseProfile(UIDTimeBasedModel):
    profile_picture = ImageField(
        upload_to=MediaHelper.get_image_upload_path,
        blank=True,
        null=True,
    )

    class Meta:
        abstract = True

    @property
    def get_profile_picture(self):
        """Return profile picture if exists, else default"""
        if self.profile_picture:
            return self.profile_picture.url
        return f"{settings.STATIC_URL}images/avatar.png"

    @property
    def full_name(self):
        """Return full name of user associated with the profile"""
        return self.user.name if self.user else "Unknown User"


class UserProfile(BaseProfile):
    user = auto_prefetch.OneToOneField(
        "users.User",
        on_delete=CASCADE,
        related_name="profile",
    )
    phone_number = CharField(max_length=15, blank=True, null=True)
    # Saved search preferences
    preferred_location = CharField(max_length=255, blank=True, null=True)
    preferred_property_type = CharField(max_length=255, blank=True, null=True)
    min_budget = DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    max_budget = DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    preferred_features = JSONField(blank=True, null=True)
    address = TextField(blank=True, null=True)
    is_premium = BooleanField(default=False)

    class Meta(auto_prefetch.Model.Meta):
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"{self.user.name}'s Profile"


class SocialMediaLinks(UIDTimeBasedModel):
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


class AgentProfile(BaseProfile):
    user = auto_prefetch.OneToOneField(
        "users.User",
        on_delete=CASCADE,
        related_name="agent_profile",
    )
    agent_type = CharField(max_length=50, choices=AgentTypeChoices.choices)
    company_name = CharField(max_length=255, blank=True, null=True)
    license_number = CharField(max_length=50, unique=True, blank=True, null=True)
    office_location = CharField(max_length=255, blank=True, null=True)
    office_phone_no = CharField(max_length=15, blank=True, null=True)
    office_address = CharField(max_length=255, blank=True, null=True)
    description = TextField(null=True, blank=True)
    rating = DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.0,
        blank=True,
        null=True,
    )
    license_document = FileField(
        upload_to=MediaHelper.get_image_upload_path,
        null=True,
        blank=True,
    )
    company_registration_document = FileField(
        upload_to=MediaHelper.get_image_upload_path,
        null=True,
        blank=True,
    )
    company_registration_number = CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
    )
    verification_status = CharField(
        max_length=20,
        choices=VerificationStatusChoices.choices,
        default=VerificationStatusChoices.PENDING,
    )
    current_subscription = auto_prefetch.OneToOneField(
        "subscriptions.AgentSubscription",
        on_delete=SET_NULL,
        null=True,
        blank=True,
        related_name="active_for_agent",
    )
    verified = BooleanField(default=False)

    class Meta(auto_prefetch.Model.Meta):
        verbose_name = "Agent Profile"
        verbose_name_plural = "Agent Profiles"
        ordering = ["-id"]

    def clean(self):
        """Validate agent-specific fields."""
        if self.agent_type == AgentTypeChoices.REAL_ESTATE_AGENT:
            if not self.company_name:
                raise ValidationError(
                    {"company_name": "Company name is required for real estate agents."}
                )
            if not self.license_number:
                raise ValidationError(
                    {
                        "license_number": "License number is required for real estate agents."
                    }
                )

    def __str__(self):
        return self.user.name

    # --- Subscription Helpers ---

    def has_active_subscription(self) -> bool:
        """Check if agent currently has a valid subscription."""
        return self.current_subscription and self.current_subscription.is_valid()

    def subscription_plan(self) -> str | None:
        """Return current subscription plan or None."""
        return self.current_subscription.plan if self.current_subscription else None

    def days_left_in_subscription(self) -> int | None:
        """Return remaining days of active subscription."""
        if not self.current_subscription:
            return None
        return self.current_subscription.remaining_days()

    def set_current_subscription(self, subscription):
        """
        Helper to assign or update current active subscription.
        Ensures only valid subscription is linked.
        """
        if subscription and not subscription.is_valid():
            raise ValidationError("Cannot assign an expired subscription.")
        self.current_subscription = subscription
        self.save(update_fields=["current_subscription"])


# class RealEstateOwnerProfile(UIDTimeBasedModel):
#     user = auto_prefetch.OneToOneField(User, on_delete=CASCADE, related_name='real_estate_profile')
#     company_name = CharField(max_length=255, blank=True, null=True)
#     company_registration_number = CharField(max_length=50, unique=True, blank=True, null=True)
#     contact_email = EmailField(unique=True, blank=True, null=True)
#     total_properties_owned = IntegerField(default=0, blank=True, null=True)
#     phone_no = CharField(max_length=15, blank=True, null=True)
#     address = TextField(blank=True, null=True)
#     profile_picture = ImageField(
#         upload_to=MediaHelper.get_image_upload_path, blank=True, null=True
#     )


#     class Meta(auto_prefetch.Model.Meta):
#         verbose_name = "Real Estate Owner Profile"
#         verbose_name_plural = "Real Estate Owner Profiles"
#         ordering = ["-id"]

#     @property
#     def full_company_details(self):
#         return f"{self.company_name} ({self.company_registration_number})"
