from allauth.account.decorators import secure_admin_login
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.utils.translation import gettext_lazy as _

from .forms import UserAdminChangeForm
from .forms import UserAdminCreationForm
from .models import (
    User, UserProfile, AgentProfile, 
    SocialMediaLinks
)

if settings.DJANGO_ADMIN_FORCE_ALLAUTH:
    # Force the `admin` sign in process to go through the `django-allauth` workflow:
    # https://docs.allauth.org/en/latest/common/admin.html#admin
    admin.autodiscover()
    admin.site.login = secure_admin_login(admin.site.login)  # type: ignore[method-assign]


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("name",)}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    list_display = ["email", "name", "role", "is_superuser"]
    search_fields = ["name"]
    ordering = ["id"]
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "role", "password1", "password2"),
            },
        ),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "phone_number", "address"]
    search_fields = ["user__name"]
    ordering = ["id"]

@admin.register(AgentProfile)
class AgentProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "office_phone_no", "office_address"]
    search_fields = ["user__name"]
    list_filter = ["verified"]
    actions = ["approve_agents"]
    ordering = ["id"]

    def approve_agents(self, request, queryset):
        queryset.update(verified=True)
        self.message_user(request, "Selected agents have been approved.")
    approve_agents.short_description = "Approve selected agents"

# @admin.register(RealEstateOwnerProfile)
# class RealEstateOwnerProfileAdmin(admin.ModelAdmin):
#     list_display = ["user", "phone_no", "address"]
#     search_fields = ["user__name"]
#     ordering = ["id"]


@admin.register(SocialMediaLinks)
class SocialMediaLinksAdmin(admin.ModelAdmin):
    list_display = ["user", "facebook", "twitter"]
    search_fields = ["user__name"]
    ordering = ["id"]