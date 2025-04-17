
from typing import ClassVar

from django.contrib.auth.models import AbstractUser
from django.db.models import CharField
from django.db.models import EmailField
from django.db.models import BooleanField, DecimalField,  IntegerField, URLField
from django.db.models import ImageField, TextField, CASCADE
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from core.helper.enums import AgentTypeChoices, UserRoleChoice
from core.helper.media import MediaHelper
from core.helper.models import UIDTimeBasedModel
from django.conf import settings

from .managers import UserManager
import auto_prefetch


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
        _("Role"), max_length=50, blank=True, null=True,
        choices=UserRoleChoice.choices
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
        elif self.role == UserRoleChoice.REAL_ESTATE_OWNER.value:
            return reverse("users:real_estate_owner_profile", kwargs={"pk": self.id})
        return reverse("users:user_profile", kwargs={"pk": self.id})
    
    @property
    def is_customer(self) -> bool:
        return self.role == self.RoleChoices.CUSTOMER.value

    @property
    def is_agent(self) -> bool:
        return self.role == self.RoleChoices.AGENT.value

    @property
    def is_real_estate_owner(self) -> bool:
        return self.role == self.RoleChoices.REAL_ESTATE_OWNER.value


class UserProfile(UIDTimeBasedModel):
    user = auto_prefetch.OneToOneField("users.User", on_delete=CASCADE, related_name="profile")
    phone_number = CharField(max_length=15, blank=True, null=True)
    address = TextField(blank=True, null=True)
    profile_picture = ImageField(
        upload_to=MediaHelper.get_image_upload_path,
        blank=True, null=True
    )
    is_premium = BooleanField(default=False)

    class Meta(auto_prefetch.Model.Meta):
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"{self.user.name}'s Profile"



class SocialMediaLinks(UIDTimeBasedModel):
    user = auto_prefetch.OneToOneField(
        "users.User", on_delete=CASCADE, related_name="social_media_links"
    )
    facebook = URLField(max_length=255, blank=True, null=True)
    twitter = URLField(max_length=255, blank=True, null=True)
    linkedin = URLField(max_length=255, blank=True, null=True)
    instagram = URLField(max_length=255, blank=True, null=True)

    class Meta(auto_prefetch.Model.Meta):
        verbose_name = "Social Media Links"
        verbose_name_plural = "Social Media Links"
        ordering = ["-id"]



class AgentProfile(UIDTimeBasedModel):
    user = auto_prefetch.OneToOneField(
        "users.User", on_delete=CASCADE, related_name='agent_profile'
    )
    agent_type = CharField(
        max_length=50, choices=AgentTypeChoices.choices,
        default=AgentTypeChoices.PROPERTY_MANAGER
    )
    company_name = CharField(max_length=255, blank=True, null=True)
    license_number = CharField(max_length=50, unique=True, blank=True, null=True)
    profile_picture = ImageField(
        upload_to=MediaHelper.get_image_upload_path, blank=True, null=True
    )
    office_location = CharField(max_length=255, blank=True, null=True)
    office_phone_no = CharField(max_length=15, blank=True, null=True)
    office_address = CharField(max_length=255, blank=True, null=True)
    description = TextField(null=True, blank=True)
    rating = DecimalField(
        max_digits=3, decimal_places=2, default=0.0,
        blank=True, null=True
    )
    verified = BooleanField(default=False)


    # def clean(self):
    #     cleaned_data = super().clean()
    #     agent_type = cleaned_data.get("agent_type")

    #     if agent_type == AgentTypeChoices.REAL_ESTATE_AGENT.value:
    #         if not cleaned_data.get("license_number"):
    #             self.add_error(
    #                 "license_number", 
    #                 "License number is required for real estate agents."
    #             )
    #         if not cleaned_data.get("company_name"):
    #             self.add_error(
    #                 "company_name", 
    #                 "Company name is required for real estate agents."
    #             )

    class Meta(auto_prefetch.Model.Meta):
        verbose_name = "Agent Profile"
        verbose_name_plural = "Agent Profiles"
        ordering = ["-id"]

    @property
    def full_name(self):
        return self.user.name if self.user else "Unknown Agent"

    @property
    def get_profile_picture(self):
        if self.profile_picture:
            return self.profile_picture.url
        return f'{settings.STATIC_URL}images/avatar.png'

    @property
    def facebook(self):
        return self.user.social_media_links.facebook if hasattr(
            self.user, "social_media_links"
        ) else None

    @property
    def twitter(self):
        return self.user.social_media_links.twitter if hasattr(
            self.user, "social_media_links"
        ) else None

    @property
    def linkedin(self):
        return self.user.social_media_links.linkedin if hasattr(
            self.user, "social_media_links"
        ) else None

    @property
    def instagram(self):
        return self.user.social_media_links.instagram if hasattr(
            self.user, "social_media_links"
        ) else None
class RealEstateOwnerProfile(UIDTimeBasedModel):
    user = auto_prefetch.OneToOneField(User, on_delete=CASCADE, related_name='real_estate_profile')
    company_name = CharField(max_length=255, blank=True, null=True)
    company_registration_number = CharField(max_length=50, unique=True, blank=True, null=True)
    contact_email = EmailField(unique=True, blank=True, null=True)
    total_properties_owned = IntegerField(default=0, blank=True, null=True)
    phone_no = CharField(max_length=15, blank=True, null=True)
    address = TextField(blank=True, null=True)
    profile_picture = ImageField(
        upload_to=MediaHelper.get_image_upload_path, blank=True, null=True
    )


    class Meta(auto_prefetch.Model.Meta):
        verbose_name = "Real Estate Owner Profile"
        verbose_name_plural = "Real Estate Owner Profiles"
        ordering = ["-id"]

    @property
    def full_company_details(self):
        return f"{self.company_name} ({self.company_registration_number})"