from django.db import models

from core.helper.models import TitleTimeBasedModel
import auto_prefetch
# Create your models here.


class Messages(TitleTimeBasedModel):
    sender = auto_prefetch.ForeignKey(
        "users.User", related_name="sent_messages", 
        on_delete=models.CASCADE
    )
    receiver = auto_prefetch.ForeignKey(
        "users.User", related_name="received_messages", 
        on_delete=models.CASCADE
    )
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class ViewingSchedule(TitleTimeBasedModel):
        user = auto_prefetch.ForeignKey("users.User", on_delete=models.CASCADE)
        property = auto_prefetch.ForeignKey("property.Property", on_delete=models.CASCADE)
        agent = auto_prefetch.ForeignKey("users.AgentProfile", on_delete=models.CASCADE)
        scheduled_date = models.DateTimeField()
        status = models.CharField(
            max_length=50, choices=[
                ("pending", "Pending"), 
                ("completed", "Completed")
            ]
        )



    class Notification(TitleTimeBasedModel):
        user = auto_prefetch.ForeignKey("users.User", on_delete=models.CASCADE)
        message = models.TextField()
        is_read = models.BooleanField(default=False)


class NotificationPreference(TitleTimeBasedModel):
    user = auto_prefetch.OneToOneField("users.User", on_delete=models.CASCADE)
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=False)
