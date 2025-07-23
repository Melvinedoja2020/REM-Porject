from django.contrib import admin

from .models import Announcement
from .models import Message
from .models import Notification
from .models import NotificationPreference

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


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ["title", "created_at", "updated_at", "visible"]
    search_fields = ["title", "content"]
    list_filter = ["created_at", "updated_at"]
    ordering = ["-created_at"]
