# Create your views here.
from django.utils import timezone
import logging

import uuid

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import DetailView
from django.views.generic import FormView
from django.views.generic import ListView
from django.views.generic import UpdateView

# from core.applications.notifications.utils.notifications import notify_new_property_listing, notify_price_change
from core.applications.property.forms import LeadCreateForm
from core.applications.property.forms import LeadStatusForm
from core.applications.property.forms import PropertyForm
from core.applications.property.forms import PropertyImageForm
from core.applications.property.forms import PropertySubscriptionForm
from core.applications.property.forms import ViewingScheduleForm
from core.applications.property.models import FavoriteProperty
from core.applications.property.models import Lead
from core.applications.property.models import Property
from core.applications.property.models import PropertyImage
from core.applications.property.models import PropertySubscription
from core.applications.property.models import PropertyType
from core.applications.property.models import PropertyViewing
from core.applications.subscriptions.features import FEATURE_LIMITS
from core.applications.subscriptions.models import FeaturedListing
from core.helper.enums import Lead_Status_Choices, SubscriptionPlan
from core.helper.enums import LeadStatus
from core.helper.enums import PropertyListingType
from core.helper.enums import UserRoleChoice
from core.helper.mixins import AgentApprovalRequiredMixin
from core.utils.notifications import notify_new_property_listing
from core.utils.notifications import notify_price_change
from core.utils.utils import process_new_lead
from core.utils.utils import process_viewing_scheduled

logger = logging.getLogger(__name__)


class PropertyCreateView(
    LoginRequiredMixin,
    UserPassesTestMixin,
    AgentApprovalRequiredMixin,
    CreateView,
):
    """
    Handles property creation for agents with plan-based restrictions.
    - Enforces property limit based on agent’s subscription.
    - Assigns agent and listing type automatically.
    - Handles property images.
    """

    model = Property
    form_class = PropertyForm
    template_name = "pages/dashboard/create_property.html"
    success_url = reverse_lazy("property:property_list")

    def test_func(self):
        return getattr(self.request.user, "role", None) == UserRoleChoice.AGENT.value

    def handle_no_permission(self):
        messages.error(self.request, "You are not authorized to create a property.")
        return redirect("home:home")

    def form_valid(self, form):
        agent_profile = self.request.user.agent_profile
        form.instance.agent = agent_profile

        # ✅ Verify subscription limit at view level (failsafe)
        subscription = getattr(agent_profile, "current_subscription", None)
        plan = subscription.plan if subscription else SubscriptionPlan.FREE
        property_count = agent_profile.properties.count()
        limit = FEATURE_LIMITS.get(plan, {}).get("properties")

        if limit is not None and property_count >= limit:
            messages.error(
                self.request,
                f"You have reached your property limit ({limit}) for the {plan} plan. "
                f"Please upgrade your subscription to add more properties.",
            )
            return redirect("subscriptions:start")  # adjust this URL as needed

        # ✅ Handle dynamic property type creation
        new_property_type = form.cleaned_data.get("new_property_type")
        if new_property_type:
            property_type = PropertyType.objects.filter(
                title__iexact=new_property_type
            ).first()
            if not property_type:
                property_type = PropertyType.objects.create(title=new_property_type)
            form.instance.property_type = property_type

        # ✅ Set default listing type
        if agent_profile.agent_type == "Real Estate Agent":
            form.instance.property_listing = PropertyListingType.FOR_SALE

        # ✅ Try saving safely
        try:
            response = super().form_valid(form)
        except ValidationError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)

        # ✅ Send notifications if property is available
        if self.object.is_available:
            notify_new_property_listing(self.object)

        # ✅ Handle image uploads
        for image in self.request.FILES.getlist("images"):
            PropertyImage.objects.create(property=self.object, image=image)

        messages.success(self.request, "✅ Property created successfully!")
        return response

    def form_invalid(self, form):
        messages.error(
            self.request, "⚠️ Error creating property. Please check the form."
        )
        return super().form_invalid(form)


class PropertyUpdateView(
    LoginRequiredMixin,
    AgentApprovalRequiredMixin,
    UserPassesTestMixin,
    UpdateView,
):
    """
    Handles property updates for agents.
    - Ensures the agent owns the property.
    - Updates property type dynamically.
    - Notifies subscribers of price changes.
    """

    model = Property
    form_class = PropertyForm
    template_name = "pages/dashboard/create_property.html"
    success_url = reverse_lazy("property:property_list")

    def test_func(self):
        user = self.request.user
        return (
            getattr(user, "role", None) == UserRoleChoice.AGENT.value
            and self.get_object().agent == user.agent_profile
        )

    def handle_no_permission(self):
        messages.error(self.request, "You are not authorized to update this property.")
        return redirect("home:home")

    def form_valid(self, form):
        property_instance = self.get_object()
        old_price = property_instance.price

        # ✅ Handle property type updates
        new_property_type = form.cleaned_data.get("new_property_type")
        if new_property_type:
            property_type = PropertyType.objects.filter(
                title__iexact=new_property_type
            ).first()
            if not property_type:
                property_type = PropertyType.objects.create(title=new_property_type)
            form.instance.property_type = property_type

        if not form.instance.agent:
            form.instance.agent = self.request.user.agent_profile

        try:
            response = super().form_valid(form)
        except ValidationError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)

        # ✅ Notify users if price changed
        if self.object.is_available and old_price != self.object.price:
            notify_price_change(self.object, old_price)

        # ✅ Handle image uploads
        for image in self.request.FILES.getlist("images"):
            PropertyImage.objects.create(property=self.object, image=image)

        messages.success(self.request, "✅ Property updated successfully!")
        return response

    def form_invalid(self, form):
        messages.error(
            self.request, "⚠️ Error updating property. Please check the form."
        )
        return super().form_invalid(form)


class PropertyDetailView(DetailView):
    """Displays property details."""

    model = Property
    template_name = "pages/dashboard/property_detail.html"
    context_object_name = "property"


class PropertyListView(
    LoginRequiredMixin,
    ListView,
):
    """Lists properties belonging to the logged-in agent."""

    model = Property
    template_name = "pages/dashboard/property_list.html"
    context_object_name = "properties"
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, "agent_profile"):
            return Property.objects.filter(agent=user.agent_profile).order_by("-id")
        return Property.objects.none()


class PropertyDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Allows agents to delete their own properties."""

    model = Property
    template_name = "pages/dashboard/property_confirm_delete.html"
    success_url = reverse_lazy("property:property_list")

    def test_func(self):
        property_obj = self.get_object()
        return property_obj.agent == getattr(self.request.user, "agent_profile", None)

    def handle_no_permission(self):
        messages.error(self.request, "You are not authorized to delete this property.")
        return redirect("property:property_list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "🗑️ Property deleted successfully!")
        return super().delete(request, *args, **kwargs)


class PropertyImageCreateView(LoginRequiredMixin, CreateView):
    model = PropertyImage
    form_class = PropertyImageForm
    template_name = "property/property_image_form.html"

    def form_valid(self, form):
        """Ensure images are associated with the correct property."""
        property_obj = get_object_or_404(Property, id=self.kwargs["property_id"])
        form.instance.property = property_obj
        response = super().form_valid(form)
        messages.success(self.request, "Image uploaded successfully!")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Error uploading image. Please try again.")
        return super().form_invalid(form)


class PropertyImageDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = PropertyImage
    template_name = "property/property_image_confirm_delete.html"

    def test_func(self):
        """Ensure only the property owner can delete images."""
        image = self.get_object()
        return image.property.agent == self.request.user.agent_profile

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Image deleted successfully!")
        return super().delete(request, *args, **kwargs)


# API View to handle image uploads via AJAX
def upload_property_images(request, property_id):
    if request.method == "POST" and request.FILES:
        property_obj = get_object_or_404(Property, id=property_id)

        images = request.FILES.getlist("images")
        for image in images:
            PropertyImage.objects.create(property=property_obj, image=image)

        return JsonResponse({"message": "Images uploaded successfully!"}, status=200)

    return JsonResponse({"error": "Invalid request"}, status=400)


class FavoriteListView(LoginRequiredMixin, ListView):
    model = FavoriteProperty
    template_name = "pages/dashboard/customers_favorite_list.html"
    context_object_name = "favorites"

    def get_queryset(self):
        return (
            FavoriteProperty.objects.filter(user=self.request.user)
            .select_related("property")
            .prefetch_related("property__images", "property__amenities")
        )


class FeaturePropertyView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Allows an agent to feature (boost) a property within their subscription limits.
    """

    def test_func(self):
        """Only agents can feature properties."""
        return getattr(self.request.user, "role", None) == UserRoleChoice.AGENT.value

    def handle_no_permission(self):
        """Redirect unauthorized users."""
        messages.error(self.request, "You are not authorized to feature properties.")
        return redirect("home:home")

    def post(self, request, *args, **kwargs):
        """Feature a property if within subscription limits."""
        property_obj = get_object_or_404(Property, pk=kwargs["pk"])
        agent = request.user.agent_profile

        # Ownership check
        if property_obj.agent != agent:
            messages.error(request, "You can only feature your own properties.")
            return redirect("property:property_list")

        # Plan check
        subscription = getattr(agent, "current_subscription", None)
        plan = subscription.plan if subscription else SubscriptionPlan.FREE
        limit = FEATURE_LIMITS.get(plan, {}).get("featured_listings")

        active_boosts = agent.featured_properties.filter(is_active=True).count()

        if limit is not None and active_boosts >= limit:
            messages.error(
                request,
                f"You've reached your featured property limit ({limit}) for the {plan} plan. "
                "Please upgrade your subscription to feature more listings.",
            )
            return redirect("subscriptions:start")

        # ✅ Prevent duplicates (deactivate existing boosts)
        agent.featured_properties.filter(property=property_obj, is_active=True).update(
            is_active=False
        )

        # ✅ Create new boost
        end_date = timezone.now() + timezone.timedelta(days=7)
        FeaturedListing.objects.create(
            property=property_obj,
            agent=agent,
            boost_duration=7,
            end_date=end_date,
            is_active=True,
        )

        messages.success(
            request, f"✅ '{property_obj.title}' is now featured for 7 days!"
        )
        return redirect("property:property_list")


class UnfeaturePropertyView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Allows an agent to unfeature (remove boost) from their property.
    """

    def test_func(self):
        """Only agents can unfeature properties."""
        return getattr(self.request.user, "role", None) == UserRoleChoice.AGENT.value

    def handle_no_permission(self):
        """Redirect unauthorized users."""
        messages.error(self.request, "You are not authorized to unfeature properties.")
        return redirect("home:home")

    def post(self, request, *args, **kwargs):
        """Unfeature a property."""
        property_obj = get_object_or_404(Property, pk=kwargs["pk"])
        agent = request.user.agent_profile

        # Ownership check
        if property_obj.agent != agent:
            messages.error(request, "You can only unfeature your own properties.")
            return redirect("property:property_list")

        # Deactivate all active featured listings for this property
        updated = FeaturedListing.objects.filter(
            property=property_obj, agent=agent, is_active=True
        ).update(is_active=False)

        if updated:
            messages.success(
                request,
                f"✅ '{property_obj.title}' has been unfeatured successfully.",
            )
        else:
            messages.info(
                request,
                f"'{property_obj.title}' is not currently featured.",
            )

        return redirect("property:property_list")


# class FavoriteDetailView(LoginRequiredMixin, DetailView):
#     model = FavoriteProperty
#     template_name = "pages/dashboard/favorite_property_detail.html"
#     context_object_name = "favorite"
#     form_class = LeadCreateForm

#     def get_queryset(self):
#         """Limit favorites to those owned by the logged-in user."""
#         return FavoriteProperty.objects.filter(user=self.request.user)

#     def get_context_data(self, **kwargs):
#         """Add lead form to the context."""
#         context = super().get_context_data(**kwargs)
#         if 'form' not in context:
#             context['form'] = self.get_form()
#         return context

#     def get_form(self):
#         """Return an initialized form instance."""
#         favorite = self.get_object()
#         return self.form_class(
#             user=self.request.user,
#             property_queryset=FavoriteProperty.objects.filter(
#                 property=favorite.property
#             ),
#             initial={'property_link': favorite.property}
#         )

#     def post(self, request, *args, **kwargs):
#         """Handle POST request to create a lead."""
#         if not request.user.is_customer:
#             raise PermissionDenied("Only customers can create leads")

#         favorite = self.get_object()
#         form = self.form_class(
#             request.POST,
#             user=request.user,
#             property_queryset=FavoriteProperty.objects.filter(
#                 property=favorite.property
#             )
#         )

#         if not form.is_valid():
#             return self.render_to_response(self.get_context_data(form=form))

#         return self.process_lead_creation(form, favorite.property)

#     @transaction.atomic
#     def process_lead_creation(self, form, property):
#         """Process the creation of a new lead with transaction safety."""
#         try:
#             # Check for existing lead
#             existing_lead = Lead.objects.select_for_update().filter(
#                 user=self.request.user,
#                 property_link=property
#             ).first()

#             if existing_lead:
#                 messages.info(
#                     self.request,
#                     self.get_existing_lead_message(existing_lead),
#                     extra_tags='alert-info'
#                 )
#                 return redirect(existing_lead.get_absolute_url())

#             # Create a new lead
#             lead = form.save(commit=False)
#             lead.user = self.request.user
#             lead.agent = property.agent
#             lead.save()

#             self.process_lead_notifications(lead)

#             messages.success(
#                 self.request,
#                 self.get_success_message(lead),
#                 extra_tags='alert-success'
#             )
#             return redirect(self.get_success_url(lead))

#         except IntegrityError as e:
#             logger.error(f"Lead creation error: {str(e)}", exc_info=True)
#             return self.handle_creation_error(form)

#     def get_existing_lead_message(self, lead):
#         """Generate message if lead already exists."""
#         return (
#             f"You already have an active inquiry (#{lead.id}) for this property. "
#             f"Last updated on {lead.updated_at.strftime('%b %d, %Y')}. "
#             "We've redirected you to your existing inquiry."
#         )

#     def get_success_message(self, lead):
#         """Generate success message on lead creation."""
#         return (
#             f"Your inquiry (#{lead.id}) has been submitted successfully! "
#             f"Agent {lead.agent.user.get_full_name()} will contact you shortly."
#         )

#     def get_success_url(self, lead):
#         """Return URL to redirect after successful lead creation."""
#         return reverse_lazy("property:lead_detail", kwargs={"pk": lead.pk})

#     def process_lead_notifications(self, lead):
#         """Send notifications after lead creation."""
#         logger.info(f"Processing new lead #{lead.id}")
#         process_new_lead(lead)

#     def handle_creation_error(self, form):
#         """Handle lead creation errors gracefully."""
#         messages.error(
#             self.request,
#             "We couldn't process your inquiry due to a system error. "
#             "Our team has been notified and will follow up shortly.",
#             extra_tags='alert-danger'
#         )
#         return self.render_to_response(self.get_context_data(form=form))


# views.py
class FavoriteLeadCreateView(LoginRequiredMixin, CreateView):
    """
    Allows a customer to create a Lead from one of their Favorite Properties.

    ✅ Rules:
    - Only authenticated customers can create leads.
    - Prevents duplicate leads for the same property.
    - Pre-fills property information from the FavoriteProperty.
    - Redirects to the Lead Detail if duplicate, else Lead List after creation.
    """

    model = Lead
    form_class = LeadCreateForm
    template_name = "pages/property/lead_create.html"
    success_url = reverse_lazy("property:lead_list")

    # -----------------------------------------------------
    # Access Control
    # -----------------------------------------------------
    def dispatch(self, request, *args, **kwargs):
        if not getattr(request.user, "is_customer", False):
            raise PermissionDenied("Only customers can create leads.")
        return super().dispatch(request, *args, **kwargs)

    # -----------------------------------------------------
    # Helpers
    # -----------------------------------------------------
    def get_favorite_property(self):
        """Retrieve the FavoriteProperty entry belonging to this user."""
        return get_object_or_404(
            FavoriteProperty.objects.select_related("property"),
            pk=self.kwargs["pk"],
            user=self.request.user,
        )

    def get_form_kwargs(self):
        """Inject user and prefill property into form."""
        kwargs = super().get_form_kwargs()
        favorite = self.get_favorite_property()
        kwargs["user"] = self.request.user
        kwargs["initial"] = {"property_link": favorite.property}
        return kwargs

    # -----------------------------------------------------
    # Form Logic
    # -----------------------------------------------------
    @transaction.atomic
    def form_valid(self, form):
        """Create a new Lead, ensuring no duplicates and full integrity."""
        user = self.request.user
        property_link = form.cleaned_data.get("property_link")

        try:
            # Lock and check for duplicate lead
            existing_lead = (
                Lead.objects.select_for_update()
                .filter(user=user, property_link=property_link)
                .first()
            )
            if existing_lead:
                messages.info(
                    self.request,
                    self._existing_lead_message(existing_lead),
                    extra_tags="alert-info",
                )
                return redirect("property:lead_detail", pk=existing_lead.pk)

            # Assign relationships
            form.instance.user = user
            form.instance.agent = getattr(property_link, "agent", None)
            form.instance.status = Lead_Status_Choices.NEW

            response = super().form_valid(form)

            # Trigger post-creation handler (email & notifications)
            process_new_lead(self.object)
            logger.debug(f"Processed new lead #{self.object.id}")

            messages.success(
                self.request,
                self._success_message(),
                extra_tags="alert-success",
            )
            # ✅ Always redirect to Lead List
            return redirect(self.get_success_url())

        except IntegrityError as exc:
            logger.error("Lead creation failed: %s", exc, exc_info=True)
            messages.error(
                self.request,
                "A system error occurred while creating your lead. Please try again later.",
                extra_tags="alert-danger",
            )
            return self.form_invalid(form)

    # -----------------------------------------------------
    # Messages
    # -----------------------------------------------------
    def _existing_lead_message(self, lead):
        """Message shown when user tries to duplicate a lead."""
        return (
            f"You already have an active lead (#{lead.id}) for this property. "
            f"Last updated on {lead.updated_at:%b %d, %Y}. "
            "Redirecting you to that lead."
        )

    def _success_message(self):
        """Success message after creation."""
        agent_name = (
            self.object.agent.user.get_full_name()
            if self.object.agent and self.object.agent.user
            else "the assigned agent"
        )
        return (
            f"New lead #{self.object.id} created successfully! "
            f"{agent_name} will reach out to you shortly."
        )


# ---------------------------------------------------------------------
# Lead List View
# ---------------------------------------------------------------------
class LeadListView(LoginRequiredMixin, ListView):
    """
    Display all leads for the logged-in customer.

    Features:
    - Restricted to the customer's own leads.
    - Prefetches related Property and Agent for performance.
    """

    model = Lead
    template_name = "pages/property/lead_list.html"
    context_object_name = "leads"
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        if getattr(user, "is_customer", False):
            return Lead.objects.select_related(
                "property_link", "agent", "agent__user"
            ).filter(user=user)
        elif getattr(user, "is_agent", False):
            return Lead.objects.select_related(
                "property_link", "agent", "agent__user"
            ).filter(property_link__agent=user.agent_profile)

        else:
            raise PermissionDenied("You do not have permission to view this lead.")


# ----------------------------------------------------------------
# Lead Update View
# ----------------------------------------------------------------
class LeadUpdateView(LoginRequiredMixin, UpdateView):
    """
    Allows an agent to update a Lead's status or notes.

    Rules:
    - Only the assigned agent or staff can update.
    - Customers cannot update the lead.
    """

    model = Lead
    form_class = LeadCreateForm  # could have a separate form for agent updates
    template_name = "pages/property/lead_update.html"
    pk_url_kwarg = "pk"

    def get_queryset(self):
        user = self.request.user
        if getattr(user, "is_agent", False):
            # Agent can update only their assigned leads
            return super().get_queryset().filter(agent=user.agent_profile)
        elif user.is_staff:
            # Staff/admin can update all leads
            return super().get_queryset()
        else:
            # Customers or others cannot update
            raise PermissionDenied("You do not have permission to update this lead.")

    def form_valid(self, form):
        messages.success(self.request, "Lead updated successfully")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("property:lead_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["property"] = self.object.property_link
        return context


# ---------------------------------------------------------------------
# Lead Detail View
# ---------------------------------------------------------------------
class LeadDetailView(LoginRequiredMixin, DetailView):
    """
    Display detailed information about a single Lead.

    Features:
    - Restricted to owner (customer).
    - Includes related property and agent details.
    """

    model = Lead
    template_name = "pages/property/lead_detail.html"
    context_object_name = "lead"

    def get_queryset(self):
        user = self.request.user
        if getattr(user, "is_customer", False):
            return Lead.objects.select_related(
                "property_link", "agent", "agent__user"
            ).filter(user=user)
        elif getattr(user, "is_agent", False):
            return Lead.objects.select_related(
                "property_link", "agent", "agent__user"
            ).filter(property_link__agent=user.agent_profile)

        else:
            raise PermissionDenied("You do not have permission to view this lead.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = Lead_Status_Choices.choices
        return context


class FavoriteDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        favorite = get_object_or_404(
            FavoriteProperty,
            pk=kwargs["pk"],
            user=request.user,
        )
        favorite.delete()
        return redirect("property:customers_favorite_list")


class PropertySubscriptionListView(LoginRequiredMixin, ListView):
    model = PropertySubscription
    template_name = "subscriptions/list.html"
    context_object_name = "subscriptions"

    def get_queryset(self):
        return self.model.objects.filter(user=self.request.user)


class CreatePropertySubscriptionView(LoginRequiredMixin, FormView):
    form_class = PropertySubscriptionForm
    template_name = "pages/dashboard/subscription_form.html"
    success_url = reverse_lazy("users:user_dashboard")

    def form_valid(self, form):
        subscription, created = PropertySubscription.objects.get_or_create(
            user=self.request.user,
            location=form.cleaned_data["location"],
            property_type=form.cleaned_data["property_type"],
        )
        if created:
            messages.success(
                self.request,
                "✅ Subscribed successfully to property alerts.",
            )
        else:
            messages.info(
                self.request,
                "ℹ️ You’re already subscribed to this preference.",
            )
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(
            self.request,
            "❌ There was an error with your subscription. Please try again.",
        )
        return super().form_invalid(form)


class PropertySubscriptionUpdateView(LoginRequiredMixin, UpdateView):
    model = PropertySubscription
    form_class = PropertySubscriptionForm
    template_name = "subscriptions/form.html"
    success_url = reverse_lazy("subscriptions:list")

    def get_queryset(self):
        return self.model.objects.filter(user=self.request.user)


class PropertySubscriptionDeleteView(LoginRequiredMixin, DeleteView):
    model = PropertySubscription
    template_name = "subscriptions/confirm_delete.html"
    success_url = reverse_lazy("subscriptions:list")

    def get_queryset(self):
        return self.model.objects.filter(user=self.request.user)


class ViewingScheduleView(AgentApprovalRequiredMixin, CreateView):
    model = PropertyViewing
    form_class = ViewingScheduleForm
    template_name = "pages/property/viewing_schedule.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.lead = get_object_or_404(
            Lead,
            pk=kwargs["pk"],
            agent=request.user.agent_profile,
        )
        # Store the lead ID in the view instance
        self.lead_id = kwargs["pk"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["lead"] = self.lead
        return context

    def form_valid(self, form):
        with transaction.atomic():
            viewing = form.save(commit=False)
            viewing.user = self.lead.user
            viewing.property = self.lead.property_link  # ✅ This is correct now
            viewing.lead = self.lead
            viewing.save()
            process_viewing_scheduled(viewing)

            self.lead.status = LeadStatus.VIEWING_SCHEDULED
            self.lead.scheduled_viewing = viewing  # ✅ Optional if used
            self.lead.save()

        messages.success(self.request, "Viewing scheduled successfully")
        return redirect(self.get_success_url())

    def get_success_url(self):
        # Use the stored lead_id to generate the URL
        return reverse_lazy("property:lead_detail", kwargs={"pk": self.lead_id})


class LeadStatusUpdateView(LoginRequiredMixin, UpdateView):
    model = Lead
    form_class = LeadStatusForm
    template_name = "pages/property/lead_status_update.html"
    pk_url_kwarg = "pk"

    def get_queryset(self):
        return Lead.objects.filter(agent=self.request.user.agent_profile)

    def form_valid(self, form):
        messages.success(self.request, "Lead status updated")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("property:lead_detail", kwargs={"pk": self.object.pk})
