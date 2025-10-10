# Register your models here.
from django.contrib import admin
from .models import PlanConfig, AgentSubscription, Payment


@admin.register(PlanConfig)
class PlanConfigAdmin(admin.ModelAdmin):
    list_display = ("plan", "price", "description")
    search_fields = ("plan",)
    ordering = ("price",)


@admin.register(AgentSubscription)
class AgentSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "agent",
        "plan",
        "is_active",
        "is_trial",
        "start_date",
        "end_date",
        "amount_paid",
    )
    list_filter = ("is_active", "is_trial", "plan")
    search_fields = ("agent__user__email", "plan")
    ordering = ("-start_date",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "subscription",
        "reference",
        "amount",
        "currency",
        "payment_method",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("agent__user__email", "reference")
    ordering = ("-created_at",)
