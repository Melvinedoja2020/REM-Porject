from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Q
from django.shortcuts import redirect

from core.applications.property.forms import PropertySearchForm


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    A generic mixin to restrict views to specific user roles.
    Example usage:
        class SomeView(RoleRequiredMixin, View):
            required_role = UserRoleChoice.AGENT
    """

    required_role = None

    def test_func(self):
        return (
            self.request.user.is_authenticated
            and self.request.user.role == self.required_role
        )

    def handle_no_permission(self):
        return redirect("dashboard:home")


class AgentApprovalRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        print("🔥 AgentApprovalRequiredMixin dispatch called")
        if (
            hasattr(request.user, "agent_profile")
            and not request.user.agent_profile.verified
        ):
            messages.warning(
                request,
                "Your agent profile is pending approval you will have access once approved.",
            )
            return redirect("home:home")
        return super().dispatch(request, *args, **kwargs)


class AgentRequiredMixin(LoginRequiredMixin):
    """Verify that the current user is an agent"""

    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request.user, "agentprofile"):
            messages.error(request, "This section is for agents only")
            return redirect("home:home")
        return super().dispatch(request, *args, **kwargs)


class PropertySearchMixin:
    def get_filtered_queryset(self, base_queryset):
        """
        Filter the queryset based on the search form data.
        This method is called in the get_queryset method of the view.
        """
        form = PropertySearchForm(self.request.GET)

        self.search_form = form  # Store the form for access in context

        if form.is_valid():
            cd = form.cleaned_data

            q = cd.get("q")
            if q:
                base_queryset = base_queryset.filter(
                    Q(title__icontains=q) | Q(description__icontains=q),
                )

            if cd.get("location"):
                base_queryset = base_queryset.filter(location__icontains=cd["location"])

            if cd.get("property_type"):
                base_queryset = base_queryset.filter(property_type=cd["property_type"])

            if cd.get("min_price"):
                base_queryset = base_queryset.filter(price__gte=cd["min_price"])

            if cd.get("max_price"):
                base_queryset = base_queryset.filter(price__lte=cd["max_price"])

            if cd.get("min_bedrooms"):
                base_queryset = base_queryset.filter(bedrooms__gte=cd["min_bedrooms"])

            if cd.get("min_bathrooms"):
                base_queryset = base_queryset.filter(bathrooms__gte=cd["min_bathrooms"])

            if cd.get("amenities"):
                for amenity in cd["amenities"]:
                    base_queryset = base_queryset.filter(amenities=amenity)

        return base_queryset.order_by("-created_at").distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = getattr(
            self,
            "search_form",
            PropertySearchForm(self.request.GET),
        )
        return context
