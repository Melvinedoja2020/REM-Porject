from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import QuerySet
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView
from django.views.generic import DetailView
from django.views.generic import RedirectView
from django.views.generic import TemplateView
from django.views.generic import UpdateView

from core.applications.users.forms import AgentProfileForm
from core.applications.users.forms import SocialMediaLinksForm
from core.applications.users.forms import SuperCustomUserCreationForm
from core.applications.users.forms import UsersProfileForm
from core.applications.users.models import AgentProfile
from core.applications.users.models import SocialMediaLinks
from core.applications.users.models import User
from core.applications.users.models import UserProfile
from core.helper.enums import UserRoleChoice
from core.helper.mixins import RoleRequiredMixin


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    slug_field = "id"
    slug_url_kwarg = "id"


user_detail_view = UserDetailView.as_view()


class BaseProfileView(LoginRequiredMixin, DetailView):
    template_name = "users/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()

        if user.role == UserRoleChoice.AGENT.value:
            context["profile"] = user.agent_profile
        elif user.role == UserRoleChoice.CUSTOMER.value:
            context["profile"] = user.profile

        # elif user.role == UserRoleChoice.REAL_ESTATE_OWNER.value:
        #     context["profile"] = user.real_estate_owner_profile
        else:
            context["profile"] = user.profile

        return context


class UserProfileView(LoginRequiredMixin, UpdateView):
    model = UserProfile
    form_class = UsersProfileForm
    template_name = "users/user_profile.html"

    def get_object(self, queryset=None):
        """Get or create user profile for the logged-in user."""
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

    def get_context_data(self, **kwargs):
        """Include social media form and profile picture in the context."""
        context = super().get_context_data(**kwargs)
        social_media, _ = SocialMediaLinks.objects.get_or_create(user=self.request.user)
        context["social_media_form"] = SocialMediaLinksForm(instance=social_media)
        context["profile_picture"] = self.get_object().get_profile_picture
        return context

    def get_form_kwargs(self):
        """Include the logged-in user in form kwargs."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def post(self, request, *args, **kwargs):
        """Handle POST for both user profile and social media form."""
        self.object = self.get_object()
        profile_form = self.get_form()
        social_media_form = SocialMediaLinksForm(
            request.POST,
            instance=self.object.user.social_media_links,
        )

        if profile_form.is_valid() and social_media_form.is_valid():
            profile_form.save()
            social_media_form.save()
            messages.success(request, "Your profile was updated successfully.")
            return redirect("users:user_profile", pk=request.user.pk)

        return self.form_invalid(profile_form)


class AgentProfileView(LoginRequiredMixin, UpdateView):
    model = AgentProfile
    form_class = AgentProfileForm
    template_name = "users/agent_profile.html"

    def get_object(self, queryset: QuerySet | None = None) -> AgentProfile:
        """Get or create agent profile for the logged-in user."""
        agent_profile, created = AgentProfile.objects.get_or_create(
            user=self.request.user,
        )

        return agent_profile

    def form_valid(self, form):
        """Save the profile and show a success message."""
        form.save()
        messages.success(
            self.request,
            "Your agent profile has been updated successfully.",
        )
        return redirect("users:agent_profile", pk=self.request.user.pk)

    def get_context_data(self, **kwargs):
        """Add social media form to the context."""
        context = super().get_context_data(**kwargs)
        social_media, created = SocialMediaLinks.objects.get_or_create(
            user=self.request.user,
        )
        context["social_media_form"] = SocialMediaLinksForm(instance=social_media)
        context["profile_picture"] = self.get_object().get_profile_picture
        return context

    def post(self, request, *args, **kwargs):
        """
        Handle both AgentProfileForm and SocialMediaLinksForm submissions.
        """
        self.object = self.get_object()
        profile_form = self.get_form()
        social_media_form = SocialMediaLinksForm(
            request.POST,
            instance=self.object.user.social_media_links,
        )

        if profile_form.is_valid() and social_media_form.is_valid():
            profile_form.save()
            social_media_form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("users:agent_profile", pk=request.user.pk)

        return self.form_invalid(profile_form)

    def get_form_kwargs(self):
        """
        Pass the logged-in user to the form.
        """
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class OwnerProfileView(BaseProfileView):
    model = User
    template_name = "users/owner_profile.html"


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    fields = ["name"]
    success_message = _("Information successfully updated")

    def get_success_url(self) -> str:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user.get_absolute_url()

    def get_object(self, queryset: QuerySet | None = None) -> User:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self) -> str:
        return self.request.user.get_profile_urls()


user_redirect_view = UserRedirectView.as_view()


class AgentDashboardView(
    RoleRequiredMixin,
    LoginRequiredMixin,
    TemplateView,
):
    template_name = "users/agent_dashboard.html"
    required_role = UserRoleChoice.AGENT.value
    error_message = "Only agents can access the agent dashboard."


class SuperUserSignupView(CreateView):
    model = User
    form_class = SuperCustomUserCreationForm
    template_name = "users/superuser_signup.html"
    success_url = reverse_lazy("admin:login")


class UserDashboardView(
    RoleRequiredMixin,
    LoginRequiredMixin,
    TemplateView,
):
    template_name = "users/user_dashboard.html"
    required_role = UserRoleChoice.CUSTOMER.value
    error_message = "Only customers can access the user dashboard."
