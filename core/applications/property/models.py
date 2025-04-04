from django.db import models
import auto_prefetch
from core.helper.enums import Lead_Status_Choices, PaymentStatus, PropertyListingType, RentalApplicationChoices
from core.helper.media import MediaHelper
from core.helper.models import TimeBasedModel, TitleTimeBasedModel
from django.utils.text import slugify
from django.utils.safestring import mark_safe
from django.utils.html import format_html


class PropertyType(TitleTimeBasedModel):
    ...

 

class Property(TitleTimeBasedModel):
    agent = auto_prefetch.ForeignKey(
        "users.AgentProfile", on_delete=models.CASCADE, related_name="properties"
    )
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    property_type = auto_prefetch.ForeignKey(
        "property.PropertyType", on_delete=models.CASCADE, 
        related_name="properties", null=True, blank=True
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

    def __str__(self):
        return self.name

class Lead(TimeBasedModel):
    agent = auto_prefetch.ForeignKey(
        "users.AgentProfile", on_delete=models.CASCADE, related_name="leads"
    )
    user = auto_prefetch.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="leads"
    )
    property = auto_prefetch.ForeignKey(
        "property.Property", on_delete=models.CASCADE, related_name="interested_users"
    )
    message = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Lead_Status_Choices.choices,
        default=Lead_Status_Choices.NEW,
    )

    def __str__(self):
        return f"Lead from {self.user.email} for {self.property.title}"

    # @property
    # def status_label(self):
    #     return dict(Lead_Status_Choices.choices).get(self.status, "Unknown")


# class Payment(TimeBasedModel):
#     user = auto_prefetch.ForeignKey(
#         "users.User", on_delete=models.CASCADE, related_name="payments"
#     )
#     property = auto_prefetch.ForeignKey(
#         "property.Property", on_delete=models.CASCADE, related_name="payments"
#     )
#     amount = models.DecimalField(max_digits=10, decimal_places=2)
#     payment_method = models.CharField(
#         max_length=20, choices=[("paystack", "Paystack"), ("stripe", "Stripe")]
#     )
#     payment_status = models.CharField(
#         max_length=20,
#         choices=PaymentStatus.choices,
#         default=PaymentStatus.PENDING,
#     )
#     transaction_id = models.CharField(max_length=255, unique=True)

#     def __str__(self):
#         return f"Payment of {self.amount} by {self.user.email} for {self.property.title}"

#     @property
#     def is_successful(self):
#         return self.payment_status == PaymentStatus.SUCCESS

#     @property
#     def formatted_amount(self):
#         return f"${self.amount:,.2f}"


# class Notification(TimeBasedModel):
#     recipient = models.ForeignKey(
#         "users.User", on_delete=models.CASCADE, related_name="notifications"
#     )
#     message = models.TextField()
#     is_read = models.BooleanField(default=False)

#     def __str__(self):
#         return f"Notification for {self.recipient.email}"

#     @property
#     def short_message(self):
#         return self.message[:50] + "..." if len(self.message) > 50 else self.message
