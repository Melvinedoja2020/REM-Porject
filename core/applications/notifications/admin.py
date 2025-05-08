from django.contrib import admin
from .models import (
    Notification, NotificationPreference, 
    Message, ViewingSchedule
)
# Register your models here.

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["user", "notification_type", "is_read", "created_at"]
    search_fields = ["user__name", "notification_type"]

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["sender", "receiver", "property", "parent_message"]

@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ["user", "email_notifications", "push_notifications"]
    search_fields = ["user__name"]
    list_filter = ["email_notifications", "push_notifications"]


