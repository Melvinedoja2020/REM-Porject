from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import QuerySet
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from django.views.generic import RedirectView
from django.views.generic import UpdateView, CreateView

from core.applications.users.forms import AgentProfileForm, SocialMediaLinksForm, SuperCustomUserCreationForm
from core.applications.users.models import AgentProfile, SocialMediaLinks, User
from core.helper.enums import UserRoleChoice
from django.views.generic import TemplateView

from core.helper.mixins import AgentApprovalRequiredMixin


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
        elif user.role == UserRoleChoice.REAL_ESTATE_OWNER.value:
            context["profile"] = user.real_estate_owner_profile
        else:
            context["profile"] = user.profile
        
        return context


class UserProfileView(BaseProfileView):
    model = User
    template_name = "users/user_profile.html"


class AgentProfileView(LoginRequiredMixin, UpdateView):
    model = AgentProfile
    form_class = AgentProfileForm
    template_name = "users/agent_profile.html"

    def get_object(self, queryset: QuerySet | None=None) -> AgentProfile:
        """Get or create agent profile for the logged-in user."""
        agent_profile, created = AgentProfile.objects.get_or_create(
            user=self.request.user
        )

        return agent_profile
    
    def form_valid(self, form):
        """Save the profile and show a success message."""
        form.save()
        messages.success(
            self.request, 
            "Your agent profile has been updated successfully."
        )
        return redirect("users:agent_profile", pk=self.request.user.pk)
    
    def get_context_data(self, **kwargs):
        """Add social media form to the context."""
        context = super().get_context_data(**kwargs)
        social_media, created = SocialMediaLinks.objects.get_or_create(user=self.request.user)
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
            instance=self.object.user.social_media_links
        )

        if profile_form.is_valid() and social_media_form.is_valid():
            profile_form.save()
            social_media_form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("users:agent_profile", pk=request.user.pk)

        return self.form_invalid(profile_form)


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

    def get_object(self, queryset: QuerySet | None=None) -> User:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self) -> str:
        return self.request.user.get_profile_urls()


user_redirect_view = UserRedirectView.as_view()


class AgentDashboardView(
    LoginRequiredMixin, UserPassesTestMixin, 
    AgentApprovalRequiredMixin, TemplateView
):
    template_name = "users/agent_dashboard.html"

    def test_func(self):
        return self.request.user.role == UserRoleChoice.AGENT.value
    
    def handle_no_permission(self):
        """Redirect unauthorized users with a message"""
        messages.error(self.request, "You are not authorized to access this page.")
        return super().handle_no_permission()
    
    def get_context_data(self, **kwargs):
        """Pass dashboard data to the template"""
        context = super().get_context_data(**kwargs)



class SuperUserSignupView(CreateView):
    model = User
    form_class = SuperCustomUserCreationForm
    template_name = "users/superuser_signup.html"
    success_url = reverse_lazy('admin:login')


# superuser_signup = SuperUserSignupView.as_view()