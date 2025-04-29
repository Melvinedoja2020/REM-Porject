from django.contrib import admin
from .models import (
    Notification, NotificationPreference, 
    Message, ViewingSchedule
)
# Register your models here.

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["user", "notification_type", "is_read", "created_at"]
    search_fields = ["user__username", "notification_type"]

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["sender", "receiver", "property", "parent_message"]