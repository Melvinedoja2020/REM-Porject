from django.db import models
from core.helper.enums import NotificationType
from core.helper.models import TitleTimeBasedModel
import auto_prefetch

# Messaging between users (agent <-> user)
class Message(TitleTimeBasedModel):
    sender = auto_prefetch.ForeignKey(
        "users.User", related_name="sent_messages", on_delete=models.CASCADE
    )
    receiver = auto_prefetch.ForeignKey(
        "users.User", related_name="received_messages", on_delete=models.CASCADE
    )
    property = auto_prefetch.ForeignKey(
        "property.Property", 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        related_name="property_messages"
    )
    parent_message = auto_prefetch.ForeignKey(
        "self", 
        null=True, 
        blank=True, 
        related_name="replies", 
        on_delete=models.CASCADE
    )
    subject = models.CharField(max_length=255, blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)

    class Meta(auto_prefetch.Model.Meta):
        ordering = ["-created_at"]
        verbose_name = "Message"
        verbose_name_plural = "Messages"

    def mark_as_read(self):
        self.is_read = True
        self.save()

    def __str__(self):
        return self.title  or "Untitled Message"


# Scheduling a property viewing
class ViewingSchedule(TitleTimeBasedModel):
    user = auto_prefetch.ForeignKey("users.User", on_delete=models.CASCADE)
    property = auto_prefetch.ForeignKey("property.Property", on_delete=models.CASCADE)
    agent = auto_prefetch.ForeignKey("users.AgentProfile", on_delete=models.CASCADE)
    scheduled_date = models.DateTimeField()
    status = models.CharField(
        max_length=50,
        choices=[
            ("pending", "Pending"), 
            ("completed", "Completed")
        ],
        default="pending"
    )

    class Meta(auto_prefetch.Model.Meta):
        ordering = ["scheduled_date"]


# Notifications for users (new listings, price changes, messages, etc)
class Notification(TitleTimeBasedModel):
    user = auto_prefetch.ForeignKey("users.User", on_delete=models.CASCADE)
    notification_type = models.CharField(
        max_length=20, choices=NotificationType.choices, 
        default=NotificationType.NEW_LISTING
    )
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    property = auto_prefetch.ForeignKey(  # optional link to a property
        "property.Property", null=True, blank=True, on_delete=models.SET_NULL
    )
    link = models.URLField(blank=True, null=True)  # optional link to view more
    extra_data = models.JSONField(blank=True, null=True)

    class Meta(auto_prefetch.Model.Meta):
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} for {self.user}"

# User notification preferences
class NotificationPreference(TitleTimeBasedModel):
    user = auto_prefetch.OneToOneField("users.User", on_delete=models.CASCADE)
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=False)
    new_listing = models.BooleanField(default=True)
    price_change = models.BooleanField(default=True)
    new_message = models.BooleanField(default=True)
    viewing_update = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification Preferences for {self.user}"
