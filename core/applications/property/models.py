from __future__ import annotations

import auto_prefetch
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.html import format_html
from django.utils.text import slugify

from core.applications.property.manager import AmenityManager
from core.applications.property.manager import FavoritePropertyManager
from core.applications.property.manager import LeadManager
from core.applications.property.manager import PropertyManager
from core.applications.property.manager import PropertySubscriptionManager
from core.applications.property.manager import PropertyViewingManager
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
    "Browse by Category" section of the home page.
    (For Sale, For Rent, Short-let, …)
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

    objects = AmenityManager()
    class Meta(auto_prefetch.Model.Meta):
        ordering = ["name"]
        verbose_name = "Amenity"
        verbose_name_plural = "Amenities"

    def __str__(self) -> str:
        return self.name




class Property(TitleTimeBasedModel):
    """
    Central listing model.  Supports all three listing types visible
    in the designs: For Sale, For Rent, and Short-let (nightly pricing).

    Design cross-reference
    ----------------------
    Home page featured cards : title, cover_image, price, location,
                               property_listing, bedrooms, bathrooms,
                               sqft, is_available
    Listing page filters     : property_type, property_listing, price,
                               bedrooms, bathrooms, amenities
    Property detail          : all fields + agent + amenities + gallery
    Category grid            : property_listing → category_counts()
    Mobile card              : card fields + agent avatar
    Short-let detail         : price_suffix → '/night'
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
    # For RENT / SALE: annual or total figure.
    # For SHORT_LET: per-night rate.
    # price_suffix and price_display expose the right label automatically.
    price = models.DecimalField(max_digits=20, decimal_places=2)
    location = models.CharField(max_length=255)
    bedrooms = models.PositiveIntegerField()
    bathrooms = models.PositiveIntegerField()
    sqft = models.PositiveIntegerField(help_text="Size in square feet.")
    amenities = models.ManyToManyField(
        "property.Amenity",
        blank=True,
        related_name="properties",
    )
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
        subscription = getattr(self.agent, "current_subscription", None)
        plan = subscription.plan if subscription else SubscriptionPlan.FREE
        limit = FEATURE_LIMITS.get(plan, {}).get("properties")
        if limit is not None and self.agent.properties.count() >= limit:
            raise ValidationError(
                f"You have reached your property limit ({limit}) for the "
                f"{plan} plan. Please upgrade your subscription."
            )

    def _generate_unique_slug(self) -> str:
        base_slug = slugify(self.title)
        slug, counter = base_slug, 1
        while Property.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

    # ---- price display -----------------------------------------------------

    @property
    def formatted_price(self) -> str:
        """e.g. '$43,000.00'"""
        return f"${self.price:,.2f}"

    @property
    def price_suffix(self) -> str:
        """
        Cadence label shown after the price on the detail page.
          SHORT_LET → '/night'
          RENT      → '/year'
          SALE      → ''
        """
        mapping = {
            PropertyListingType.SHORT_LET: "/night",
            PropertyListingType.RENT: "/year",
        }
        return mapping.get(self.property_listing, "")

    @property
    def price_display(self) -> str:
        """Full string e.g. '$4,500 /night' or '$250,000'."""
        return f"{self.formatted_price} {self.price_suffix}".strip()

    @property
    def availability_label(self) -> str:
        return "Available" if self.is_available else "Not Available"

    # ---- image helpers -----------------------------------------------------

    def get_main_image(self):
        """
        Returns the cover ImageField when set, otherwise the first ordered
        gallery image.  Falls back to None.

        Note: when called inside a serializer that uses with_card_relations(),
        ``self.images.all()`` resolves from the prefetch cache — no DB hit.
        """
        if self.cover_image:
            return self.cover_image
        first = self.images.all()[:1]
        return first[0].image if first else None

    @property
    def main_image_url(self) -> str:
        image = self.get_main_image()
        return image.url if image else "/static/images/placeholder.jpg"

    @property
    def main_image_preview(self):
        """HTML thumbnail for Django admin list display."""
        return format_html(
            '<img src="{}" width="120" height="80" style="object-fit:cover;" />',
            self.main_image_url,
        )

    # ---- feature / favourite helpers ---------------------------------------

    @property
    def is_featured(self) -> bool:
        """
        True when an active FeaturedListing exists.
        On querysets that called with_featured_annotation() the annotated
        ``is_featured_now`` field is cheaper; this property is the fallback
        for single-object access.
        """
        return self.featured_listings.filter(
            is_active=True,
            end_date__gte=timezone.now(),
        ).exists()

    def is_favorited_by(self, user) -> bool:
        """
        Pass the user explicitly rather than storing on the instance —
        avoids the broken ``@property`` + ``self, user`` anti-pattern.
        Use the ``is_favorited`` queryset annotation for list views.
        """
        if not user or not user.is_authenticated:
            return False
        return self.favorited_by.filter(user=user).exists()


class PropertyImage(TimeBasedModel):
    """
    Ordered gallery images for the property detail hero carousel.
    ``Property.get_main_image()`` falls back to the first row here
    when no cover_image is set on the parent.
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


class FavoriteProperty(TimeBasedModel):
    """
    Join table between a user and a bookmarked property.
    Toggled via the favorite endpoint; rendered in the user's saved list.
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

    objects = FavoritePropertyManager()

    class Meta(auto_prefetch.Model.Meta):
        unique_together = ("user", "property")
        ordering = ["-created_at"]
        verbose_name = "Favorite Property"
        verbose_name_plural = "Favorite Properties"

    def __str__(self) -> str:
        return f"{self.user.email} ♥ {self.property.title}"




class PropertySubscription(TimeBasedModel):
    """
    Subscribes a user to new-listing notifications for a given
    location / property-type combination.
    Null values act as wildcards (any location / any type).
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

    objects = PropertySubscriptionManager()

    class Meta(auto_prefetch.Model.Meta):
        unique_together = ("user", "location", "property_type")
        verbose_name = "Property Subscription"
        verbose_name_plural = "Property Subscriptions"

    def __str__(self) -> str:
        ptype = self.property_type or "any type"
        loc = self.location or "any location"
        return f"{self.user} → {ptype} in {loc}"


# ---------------------------------------------------------------------------
# Leads
# ---------------------------------------------------------------------------


class Lead(TimeBasedModel):
    """
    Created when a user taps "Contact Agent" on a property card (mobile)
    or submits an enquiry from the detail page.

    One Lead per (user, property) pair — enforced by unique_together.
    PropertyViewing rows are children of this record via ``viewing.lead``.
    Deleting the lead does NOT cascade to viewings (SET_NULL on the child).
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
    # ``property_link`` avoids shadowing the Python built-in ``property``.
    # The ``.property`` alias below maintains backward compatibility.
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

    objects = LeadManager()

    class Meta(auto_prefetch.Model.Meta):
        unique_together = [("user", "property_link")]
        ordering = ["-created_at"]
        verbose_name = "Lead"
        verbose_name_plural = "Leads"

    # ---- aliases & helpers -------------------------------------------------

    # @property
    # def property(self):
    #     """Backward-compatible alias for ``property_link``."""
    #     return self.property_link

    @property
    def upcoming_viewing(self):
        """
        Next PENDING / CONFIRMED viewing for this lead.
        On queryset results from LeadQuerySet.with_relations(), reading
        ``upcoming_viewings_cache`` is preferred (zero extra queries).
        This property is the fallback for single-object access.
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


# ---------------------------------------------------------------------------
# Property viewings
# ---------------------------------------------------------------------------


class PropertyViewing(TimeBasedModel):
    """
    A scheduled viewing appointment.

    Design reference
    ----------------
    The mobile "Schedule a Viewing" modal (Image 5 in the Figma) collects
    date, time, and optional notes, then POSTs to create one of these.

    Business rules
    --------------
    • ``scheduled_time`` must be in the future          (clean)
    • No two PENDING/CONFIRMED viewings may share the
      same property + time slot                          (UniqueConstraint)
    • When a lead FK is provided the viewing's property
      must match the lead's property                     (clean)
    • Deleting a Lead does NOT delete its viewings;
      ``lead`` becomes NULL                              (SET_NULL)
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
        on_delete=models.SET_NULL,
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

    objects = PropertyViewingManager()

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
            raise ValidationError(
                "Viewing property must match the lead's property."
            )

    def __str__(self) -> str:
        ts = self.scheduled_time.strftime("%Y-%m-%d %H:%M")
        return f"Viewing — {self.property.title} @ {ts}"
