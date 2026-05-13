from __future__ import annotations

import auto_prefetch
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.html import format_html
from django.utils.text import slugify

from core.applications.property.manager import PropertyManager
from core.applications.subscriptions.features import FEATURE_LIMITS
from core.helpers.enums import Lead_Status_Choices
from core.helpers.enums import LeadStatus
from core.helpers.enums import PropertyListingType
from core.helpers.enums import PropertyTypeChoices
from core.helpers.enums import PropertyViewingChoices
from core.helpers.enums import SubscriptionPlan
from core.helpers.media import MediaHelper
from core.helpers.models import TimeBasedModel
from core.helpers.models import TitleTimeBasedModel

User = get_user_model()
class PropertyType(TitleTimeBasedModel):
    """
    Lookup table for property categories rendered in the
    "Browse by Category" section of the home page (For Sale, For Rent,
    Short-let, etc.).
    """

    class Meta(auto_prefetch.Model.Meta):
        ordering = ["title"]
        verbose_name = "Property Type"
        verbose_name_plural = "Property Types"


class Amenity(TimeBasedModel):
    """
    Individual amenity tag shown in the "Features & Amenities" section of
    the property detail page (e.g. Swimming Pool, Gym, Air Conditioning).
    """

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta(auto_prefetch.Model.Meta):
        ordering = ["name"]
        verbose_name = "Amenity"
        verbose_name_plural = "Amenities"

    def __str__(self) -> str:
        return self.name


# ---------------------------------------------------------------------------
# Core Property Model
# ---------------------------------------------------------------------------


class Property(TitleTimeBasedModel):
    """
    The main Property model, representing a real estate listing.  Each row is
    a unique property that can be listed for sale or rent by an agent,
    and contacted by users via leads and viewings.
    """

    agent = auto_prefetch.ForeignKey(
        "users.AgentProfile",
        on_delete=models.CASCADE,
        related_name="properties",
    )
    cover_image = models.ImageField(
        upload_to=MediaHelper.get_image_upload_path,
        null=True,
        blank=True,
    )
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    description = models.TextField()
    property_type = models.CharField(
        max_length=50,
        choices=PropertyTypeChoices.choices,
        default=PropertyTypeChoices.APARTMENT,
        null=True,
        blank=True,
    )
    property_listing = models.CharField(
        max_length=200,
        choices=PropertyListingType.choices,
        default=PropertyListingType.RENT,
    )

    # ---- pricing -----------------------------------------------------------
    # For RENT/SALE this is an annual/total figure; for SHORT_LET it is
    # per-night.  The `price_suffix` property surfaces the correct label
    # so the detail page can display "$4,500 /night" vs "$43,000 /year".
    price = models.DecimalField(max_digits=20, decimal_places=2)

    # ---- location ----------------------------------------------------------
    location = models.CharField(max_length=255)

    # ---- specs (shown as icon-badges on cards and detail page) -------------
    bedrooms = models.PositiveIntegerField()
    bathrooms = models.PositiveIntegerField()
    sqft = models.PositiveIntegerField(help_text="Size in square feet")

    # ---- relations ---------------------------------------------------------
    amenities = models.ManyToManyField(
        "property.Amenity",
        blank=True,
        related_name="properties",
    )

    # ---- availability ------------------------------------------------------
    # Drives the "Available" / "Not Available" badge on listing cards.
    is_available = models.BooleanField(default=True)

    objects = PropertyManager()

    class Meta(auto_prefetch.Model.Meta):
        ordering = ["-created_at", "-id"]
        verbose_name = "Property"
        verbose_name_plural = "Properties"


    def __str__(self) -> str:
        return f"{self.title} — {self.get_property_listing_display()}"


    def save(self, *args, **kwargs) -> None:
        """
        1. Enforce per-plan property limits on first save.
        2. Auto-generate a unique slug from the title when absent.
        """
        if not self.pk:
            self._enforce_plan_limit()

        if not self.slug:
            self.slug = self._generate_unique_slug()

        super().save(*args, **kwargs)

    def _enforce_plan_limit(self) -> None:
        """
        Checks the agent's current subscription plan and raises a ValidationError
        """
        subscription = getattr(self.agent, "current_subscription", None)
        plan = subscription.plan if subscription else SubscriptionPlan.FREE
        limit = FEATURE_LIMITS.get(plan, {}).get("properties")
        if limit is not None and self.agent.properties.count() >= limit:
            msg = (
                f"You have reached your property limit ({limit}) for the "
                f"{plan} plan. Please upgrade your subscription."
            )
            raise ValidationError(
                msg,
            )

    def _generate_unique_slug(self) -> str:
        """
        Generates a URL-friendly slug from the title, ensuring uniqueness by
        appending a counter if needed.
        """

        base_slug = slugify(self.title)
        slug, counter = base_slug, 1
        while Property.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

    # ---- computed display helpers (used by serializers / templates) --------

    @property
    def formatted_price(self) -> str:
        """e.g.  '$43,000.00'"""
        return f"${self.price:,.2f}"

    @property
    def price_suffix(self) -> str:
        """
        Returns the cadence label shown after the price on the detail page:
          Short-let  → '/night'
          Rent       → '/year'
          Sale       → ''  (no suffix needed)
        """
        if self.property_listing == PropertyListingType.SHORT_LET:
            return "/night"
        if self.property_listing == PropertyListingType.RENT:
            return "/year"
        return ""

    @property
    def price_display(self) -> str:
        """Full display string e.g.  '$4,500 /night' or '$250,000'."""
        suffix = self.price_suffix
        return f"{self.formatted_price} {suffix}".strip()

    @property
    def availability_label(self) -> str:
        return "Available" if self.is_available else "Not Available"

    @property
    def amenities_list(self) -> list[str]:
        """Flat list of amenity names for serializers."""
        return list(self.amenities.values_list("name", flat=True))

    # ---- image helpers -----------------------------------------------------

    def get_main_image(self):
        """
        Returns the cover ImageField (or the first gallery image).
        Falls back to None when no image exists at all.
        """
        if self.cover_image:
            return self.cover_image
        first = self.images.first()
        return first.image if first else None

    @property
    def main_image_url(self) -> str:
        image = self.get_main_image()
        return image.url if image else "/static/images/placeholder.jpg"

    @property
    def main_image_preview(self):
        """HTML thumbnail — useful in the Django admin list display."""
        return format_html(
            '<img src="{}" width="120" height="80" style="object-fit:cover;" />',
            self.main_image_url,
        )

    # ---- feature flags -----------------------------------------------------

    @property
    def is_featured(self) -> bool:
        """True when an active FeaturedListing exists for this property."""
        return self.featured_listings.filter(
            is_active=True,
            end_date__gte=timezone.now(),
        ).exists()

    def is_favorited_by(self, user) -> bool:
        """
        Instance method (not a property) so the user can be passed
        explicitly — avoids the broken `@property` + `self, user` signature
        that existed in the original.
        """
        if not user or not user.is_authenticated:
            return False
        return self.favorited_by.filter(user=user).exists()


# ---------------------------------------------------------------------------
# Gallery
# ---------------------------------------------------------------------------


class PropertyImage(TimeBasedModel):
    """
    Additional gallery images displayed in the property detail hero area.
    The listing uses `Property.get_main_image()` which falls back to the
    first row here when no cover_image is set.
    """

    property = auto_prefetch.ForeignKey(
        "property.Property",
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to=MediaHelper.get_image_upload_path)
    order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Lower numbers appear first in the gallery.",
    )

    class Meta(auto_prefetch.Model.Meta):
        ordering = ["order", "created_at"]
        verbose_name = "Property Image"
        verbose_name_plural = "Property Images"

    def __str__(self) -> str:
        return f"Image for {self.property.title}"


# ---------------------------------------------------------------------------
# Subscriptions & Favourites
# ---------------------------------------------------------------------------


class PropertySubscription(TimeBasedModel):
    """
    Allows a user to subscribe to new-listing alerts for a given
    location / property type combination.
    """

    user = auto_prefetch.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="property_subscriptions",
    )
    location = models.CharField(max_length=255, blank=True, null=True)
    property_type = models.CharField(
        max_length=50,
        choices=PropertyTypeChoices.choices,
        blank=True,
        null=True,
    )

    class Meta(auto_prefetch.Model.Meta):
        unique_together = ("user", "location", "property_type")
        verbose_name = "Property Subscription"
        verbose_name_plural = "Property Subscriptions"

    def __str__(self) -> str:
        ptype = self.property_type or "any type"
        loc = self.location or "any location"
        return f"{self.user} → {ptype} in {loc}"


class FavoriteProperty(TimeBasedModel):
    """
    Many-to-many join between a user and a property they have bookmarked.
    Resolved via `Property.is_favorited_by(user)` on the detail page.
    """

    user = auto_prefetch.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="favorites",
    )
    property = auto_prefetch.ForeignKey(
        "property.Property",
        on_delete=models.CASCADE,
        related_name="favorited_by",
    )

    class Meta(auto_prefetch.Model.Meta):
        unique_together = ("user", "property")
        ordering = ["-created_at"]
        verbose_name = "Favorite Property"
        verbose_name_plural = "Favorite Properties"

    def __str__(self) -> str:
        return f"{self.user.email} ♥ {self.property.title}"


# ---------------------------------------------------------------------------
# Leads & Viewings
# ---------------------------------------------------------------------------


class Lead(TimeBasedModel):
    """
    Created when a user taps "Contact Agent" on the mobile card or
    submits an enquiry from the property detail page.

    The Lead is the parent record; PropertyViewing rows (0–many) are
    attached to it via `viewing.lead`.  This keeps the enquiry history
    intact even when individual viewings are cancelled.
    """

    agent = auto_prefetch.ForeignKey(
        "users.AgentProfile",
        on_delete=models.CASCADE,
        related_name="leads",
    )
    user = auto_prefetch.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="leads",
    )
    # Named `property_link` to avoid shadowing the Python built-in;
    # the `.property` alias below preserves backward compatibility.
    property_link = auto_prefetch.ForeignKey(
        "property.Property",
        on_delete=models.CASCADE,
        related_name="leads",
    )
    message = models.TextField()
    notes = models.TextField(blank=True)
    last_contact = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Lead_Status_Choices.choices,
        default=Lead_Status_Choices.NEW,
    )

    class Meta(auto_prefetch.Model.Meta):
        unique_together = [("user", "property_link")]
        ordering = ["-created_at"]
        verbose_name = "Lead"
        verbose_name_plural = "Leads"

    # ---- helpers -----------------------------------------------------------

    @property
    def property(self):
        """Backward-compatible alias for `property_link`."""
        return self.property_link

    @property
    def upcoming_viewing(self):
        """
        Returns the next confirmed/pending viewing for this lead — used on
        the mobile scheduling modal shown in the designs.
        """
        return self.viewings.filter(
            status__in=[
                PropertyViewingChoices.PENDING,
                PropertyViewingChoices.CONFIRMED,
            ],
            scheduled_time__gte=timezone.now(),
        ).first()

    # ---- validation --------------------------------------------------------

    def clean(self) -> None:
        if self.status == LeadStatus.VIEWING_SCHEDULED and not self.viewings.exists():
            raise ValidationError(
                "At least one viewing must be scheduled before setting this status."
            )

    def __str__(self) -> str:
        return f"Lead #{self.id}: {self.user.email} → {self.property.title}"


class PropertyViewing(TimeBasedModel):
    """
    A scheduled viewing appointment.

    Design reference: the mobile "Schedule a Viewing" modal (image 5) collects
    a date, time, and optional notes then POSTs to create one of these.

    Business rules
    --------------
    * `scheduled_time` must be in the future (enforced in `clean`).
    * No two PENDING/CONFIRMED viewings may share the same property + time slot
      (enforced by the DB-level UniqueConstraint).
    * When a lead FK is provided, the viewing's property must match the lead's
      property (enforced in `clean`).
    """

    user = auto_prefetch.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="viewings",
    )
    property = auto_prefetch.ForeignKey(
        "property.Property",
        on_delete=models.CASCADE,
        related_name="viewings",
    )
    lead = auto_prefetch.ForeignKey(
        "property.Lead",
        on_delete=models.SET_NULL,       # Viewing survives lead deletion
        related_name="viewings",
        null=True,
        blank=True,
    )
    scheduled_time = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=PropertyViewingChoices.choices,
        default=PropertyViewingChoices.PENDING,
    )
    notes = models.TextField(blank=True)
    cancellation_reason = models.TextField(blank=True)

    class Meta(auto_prefetch.Model.Meta):
        ordering = ["-scheduled_time"]
        verbose_name = "Property Viewing"
        verbose_name_plural = "Property Viewings"
        constraints = [
            models.UniqueConstraint(
                fields=["property", "scheduled_time"],
                name="unique_property_viewing_time",
                condition=models.Q(status__in=["PENDING", "CONFIRMED"]),
            ),
        ]

    # ---- validation --------------------------------------------------------

    def clean(self) -> None:
        if self.scheduled_time and self.scheduled_time < timezone.now():
            raise ValidationError("Viewing time cannot be in the past.")
        if self.lead_id and self.lead.property_link_id != self.property_id:
            raise ValidationError("Viewing property must match the lead's property.")

    def __str__(self) -> str:
        ts = self.scheduled_time.strftime("%Y-%m-%d %H:%M")
        return f"Viewing — {self.property.title} @ {ts}"
