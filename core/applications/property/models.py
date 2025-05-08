from django.db import models
import auto_prefetch
from core.helper.enums import Lead_Status_Choices, LeadStatus, PaymentStatus, PropertyListingType, PropertyTypeChoices, PropertyViewingChoices, RentalApplicationChoices
from core.helper.media import MediaHelper
from core.helper.models import TimeBasedModel, TitleTimeBasedModel
from django.utils.text import slugify
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.core.exceptions import ValidationError
from django.utils import timezone


class PropertyType(TitleTimeBasedModel):
    ...

 

class Property(TitleTimeBasedModel):
    agent = auto_prefetch.ForeignKey(
        "users.AgentProfile", on_delete=models.CASCADE, related_name="properties"
    )
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    property_type = models.CharField(
        max_length=50, choices=PropertyTypeChoices.choices, 
        default=PropertyTypeChoices.APARTMENT, null=True,
        blank=True,
    )
    property_listing = models.CharField(
        max_length=200,
        choices=PropertyListingType.choices,
        default=PropertyListingType.RENT,
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    location = models.CharField(max_length=255)
    bedrooms = models.PositiveIntegerField()
    bathrooms = models.PositiveIntegerField()
    sqft = models.PositiveIntegerField(help_text="Size in square feet")
    amenities = models.ManyToManyField(
        "property.Amenity", blank=True, related_name="properties"
    )
    
    is_available = models.BooleanField(default=True)

    class Meta(auto_prefetch.Model.Meta):
        ordering = ["-created_at"]
        verbose_name = "Property"
        verbose_name_plural = "Properties"

    def __str__(self):
        return f"{self.title} - {self.property_listing}"
    


    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


    @property
    def formatted_price(self):
        return f"${self.price:,.2f}"

    @property
    def is_available_status(self):
        return "Available" if self.is_available else "Not Available"
    
    @property
    def get_amenities_list(self):
        """Returns a list of amenities as strings"""
        return list(self.amenities.values_list("name", flat=True))
    
    def get_main_image(self):
        """Returns the first associated image or None."""
        return self.images.first()
    
    @property
    def main_image_url(self):
        """Returns the URL of the main image or a default placeholder."""
        main_image = self.get_main_image()
        return main_image.image.url if main_image and main_image.image else "/static/images/placeholder.jpg"
    
    @property
    def main_image_preview(self):
        """Returns HTML for image preview (e.g. in admin)."""
        url = self.main_image_url
        return format_html('<img src="{}" width="120" height="80" style="object-fit:cover;" />', url)
    
    @property
    def is_favorited_by_user(self, user):
        if not user.is_authenticated:
            return False
        return self.favoriteproperty_set.filter(user=user).exists()


class PropertyImage(TimeBasedModel):
    property = auto_prefetch.ForeignKey(
        "property.Property", on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to=MediaHelper.get_image_upload_path)

    def __str__(self):
        return f"Image for {self.property.title}"

    # @property
    # def image_preview(self):
    #     return mark_safe(f'<img src="{self.image.url}" width="100" height="100" />')


class Amenity(TimeBasedModel):
    name = models.CharField(max_length=100)
    description = models.TextField()

    class Meta(auto_prefetch.Model.Meta):
        ordering = ["-created_at"]
        verbose_name = "Amenity"
        verbose_name_plural = "Amenities"

    def __str__(self):
        return self.name


from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class PropertySubscription(TimeBasedModel):
    user = auto_prefetch.ForeignKey(
        "users.User", on_delete=models.CASCADE, 
        related_name="property_subscriptions"
    )
    location = models.CharField(max_length=255, blank=True, null=True)
    property_type = models.CharField(
        max_length=50,
        choices=PropertyTypeChoices.choices,
        blank=True,
        null=True
    )

    class Meta(auto_prefetch.Model.Meta):
        verbose_name = "Property Subscription"
        verbose_name_plural = "Property Subscriptions"
        unique_together = (
            "user", "location", 
            "property_type"
        )

    def __str__(self):
        return f"{self.user} subscribes to {self.property_type or 'any type'} in {self.location or 'any location'}"

class FavoriteProperty(TimeBasedModel):
    user = auto_prefetch.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="favorites"
    )
    property = auto_prefetch.ForeignKey(
        "property.Property", on_delete=models.CASCADE, related_name="favorited_by"
    )

    class Meta(auto_prefetch.Model.Meta):
        unique_together = ("user", "property")
        ordering = ["-created_at"]
        verbose_name = "Favorite Property"
        verbose_name_plural = "Favorite Properties"

    def __str__(self):
        return f"{self.user.email} favorited {self.property.title}"

    # @property
    # def status_label(self):
    #     return dict(Lead_Status_Choices.choices).get(self.status, "Unknown")

class PropertyViewing(TimeBasedModel):
    user = auto_prefetch.ForeignKey("users.User", on_delete=models.CASCADE)
    property = auto_prefetch.ForeignKey("property.Property", on_delete=models.CASCADE)
    scheduled_time = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=PropertyViewingChoices.choices,
        default=PropertyViewingChoices.PENDING,
    )
    lead = auto_prefetch.ForeignKey(
        "property.Lead",
        on_delete=models.CASCADE,
        related_name="viewings",  # This is fine
        null=True,
        blank=True,
    )
    scheduled_time = models.DateTimeField()
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
                condition=models.Q(status__in=["PENDING", "CONFIRMED"])
            )
        ]

    
    def clean(self):
        if self.scheduled_time < timezone.now():
            raise ValidationError("Viewing time cannot be in the past")
        
        if self.lead and self.lead.property != self.property:
            raise ValidationError("Viewing property must match lead property")

    def __str__(self):
        return f"Viewing for {self.property.title} at {self.scheduled_time.strftime('%Y-%m-%d %H:%M')}"



class Lead(TimeBasedModel):
    agent = auto_prefetch.ForeignKey(
        "users.AgentProfile", on_delete=models.CASCADE, related_name="leads"
    )
    user = auto_prefetch.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="leads"
    )
    property_link  = auto_prefetch.ForeignKey(
        "property.Property", on_delete=models.CASCADE, related_name="interested_users"
    )
    scheduled_viewing = models.ForeignKey(
        "property.PropertyViewing",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="lead_scheduled",  
    )
    notes = models.TextField(blank=True)
    last_contact = models.DateTimeField(null=True, blank=True)
    message = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Lead_Status_Choices.choices,
        default=Lead_Status_Choices.NEW,
    )

    class Meta(auto_prefetch.Model.Meta):
        unique_together = [['user', 'property_link']]
        ordering = ['-created_at']
        verbose_name = "Lead"
        verbose_name_plural = "Leads"

    @property
    def upcoming_viewing(self):
        return self.viewings.filter(
            status__in=[PropertyViewingChoices.PENDING, PropertyViewingChoices.CONFIRMED],
            scheduled_time__gte=timezone.now()
        ).first()

    @property
    def property(self):
        """Provides backward-compatible access to property_link"""
        return self.property_link
    
    def clean(self):
        if self.status == LeadStatus.VIEWING_SCHEDULED and not self.viewings.exists():
            raise ValidationError("At least one viewing must be scheduled for this status")

    def __str__(self):
        return f"Lead #{self.id}: {self.user.email} for {self.property.title}"

    