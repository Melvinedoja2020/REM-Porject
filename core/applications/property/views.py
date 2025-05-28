import uuid
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.generic import (
    CreateView, UpdateView, ListView, DetailView, DeleteView,
    FormView
)
from django.views import View
from django.shortcuts import get_object_or_404
# from core.applications.notifications.utils.notifications import notify_new_property_listing, notify_price_change
from core.applications.property.forms import LeadCreateForm, LeadStatusForm, PropertyForm, PropertyImageForm, PropertySubscriptionForm, ViewingScheduleForm
from core.applications.property.models import FavoriteProperty, Lead, Property, PropertyImage, PropertySubscription, PropertyType, PropertyViewing
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.shortcuts import redirect

from core.helper.enums import Lead_Status_Choices, LeadStatus, PropertyListingType, UserRoleChoice
from core.helper.mixins import AgentApprovalRequiredMixin, AgentRequiredMixin
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.core.exceptions import ValidationError

from core.utils.notifications import notify_new_property_listing, notify_price_change
from django.core.exceptions import PermissionDenied

from core.utils.utils import process_new_lead, process_viewing_scheduled
# Create your views here.


import logging
logger = logging.getLogger(__name__)


class PropertyCreateView(
    LoginRequiredMixin, UserPassesTestMixin,
    AgentApprovalRequiredMixin, CreateView
):
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
        """Set the agent and listing type before saving the property."""
        new_property_type = form.cleaned_data.get("new_property_type")
        if new_property_type:
            property_type = PropertyType.objects.get(name__iexact=new_property_type)
            form.instance.property_type = property_type

        agent_profile = self.request.user.agent_profile
        form.instance.agent = agent_profile

        # Set listing type to FOR_SALE if agent is a REAL_ESTATE_AGENT
        if agent_profile.agent_type == "Real Estate Agent":
            form.instance.property_listing = PropertyListingType.FOR_SALE

        response = super().form_valid(form)

        # Notify subscribers if property is available
        if self.object.is_available:
            notify_new_property_listing(self.object)
            
        # Handle multiple image uploads
        images = self.request.FILES.getlist("images")
        for image in images:
            PropertyImage.objects.create(property=self.object, image=image)

        messages.success(self.request, "Property created successfully!")
        return response
    

    def form_invalid(self, form):
        print("❌ Form invalid. Errors:", form.errors)
        messages.error(self.request, "Error creating property. Please check the form.")
        return super().form_invalid(form)
    

class PropertyUpdateView(LoginRequiredMixin, AgentApprovalRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Property
    form_class = PropertyForm
    template_name = "pages/dashboard/create_property.html"
    success_url = reverse_lazy("property:property_list")

    def test_func(self):
        # Ensure user is an agent and owns the property
        is_agent = getattr(self.request.user, "role", None) == UserRoleChoice.AGENT.value
        is_owner = self.get_object().agent == self.request.user.agent_profile
        return is_agent and is_owner

    def handle_no_permission(self):
        messages.error(self.request, "You are not authorized to update this property.")
        return redirect("home:home")

    def form_valid(self, form):
        property_instance = self.get_object()
        old_price = property_instance.price

        new_property_type = form.cleaned_data.get('new_property_type')
        if new_property_type:
            property_type = PropertyType.objects.filter(title__iexact=new_property_type).first()
            if not property_type:
                property_type = PropertyType.objects.create(title=new_property_type)
            form.instance.property_type = property_type

        if not form.instance.agent:
            form.instance.agent = self.request.user.agent_profile

        response = super().form_valid(form)

        # Notify users if the price has changed and property is available
        if self.object.is_available and old_price != self.object.price:
            notify_price_change(self.object, old_price)

        images = self.request.FILES.getlist("images")
        for image in images:
            PropertyImage.objects.create(property=self.object, image=image)

        messages.success(self.request, "Property updated successfully!")
        return response

    def form_invalid(self, form):
        print("❌ Form invalid. Errors:", form.errors)
        messages.error(self.request, "Error updating property. Please check the form.")
        return super().form_invalid(form)


class PropertyDetailView(DetailView):
    model = Property
    template_name = "pages/dashboard/property_detail.html"
    context_object_name = "property"
    


class PropertyListView(LoginRequiredMixin, ListView):
    model = Property
    template_name = "pages/dashboard/property_list.html"
    context_object_name = "properties"
    paginate_by = 10

    def get_queryset(self):
        """Show available properties for the logged-in agent."""
        user = self.request.user
        if hasattr(user, "agent_profile"):
            return Property.objects.filter(
                is_available=True,
                agent=user.agent_profile
            ).order_by("-id")
        return Property.objects.none()


class PropertyDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Property
    template_name = "pages/dashboard/property_confirm_delete.html"
    success_url = reverse_lazy("property:property_list")

    def test_func(self):
        """Ensure only the property owner (agent) can delete."""
        property_obj = self.get_object()
        return property_obj.agent == getattr(self.request.user, "agent_profile", None)

    def handle_no_permission(self):
        messages.error(self.request, "You are not authorized to delete this property.")
        return redirect("property:property_list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Property deleted successfully!")
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
    model = Lead
    form_class = LeadCreateForm
    template_name = "pages/property/lead_create.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_customer:
            raise PermissionDenied("Only customers can create leads")
        return super().dispatch(request, *args, **kwargs)

    def get_favorite_property(self):
        return get_object_or_404(
            FavoriteProperty.objects.select_related("property"),
            pk=self.kwargs["pk"],
            user=self.request.user
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        favorite = self.get_favorite_property()
        kwargs["initial"] = {
            "property_link": favorite.property,
        }
        return kwargs

    @transaction.atomic
    def form_valid(self, form):
        try:
            property_link = form.cleaned_data["property_link"]

            existing_lead = Lead.objects.select_for_update().filter(
                user=self.request.user,
                property_link=property_link
            ).first()

            if existing_lead:
                messages.info(
                    self.request,
                    self.get_existing_lead_message(existing_lead),
                    extra_tags='alert-info'
                )
                return redirect(existing_lead.get_absolute_url())

            form.instance.user = self.request.user
            form.instance.agent = property_link.agent

            response = super().form_valid(form)

            logger.debug(f"Calling process_new_lead for lead ID <<<>>> {self.object.id}")
            process_new_lead(self.object)

            messages.success(
                self.request,
                self.get_success_message(),
                extra_tags='alert-success'
            )
            return response

        except IntegrityError as e:
            return self.handle_integrity_error(e, form)

    def get_success_url(self):
        return reverse_lazy("property:lead_detail", kwargs={"pk": self.object.pk})

    def get_existing_lead_message(self, lead):
        return (
            f"You already have an active lead (#{lead.id}) for this property. "
            f"Last updated {lead.updated_at.strftime('%b %d, %Y')}. "
            "We've redirected you to the existing lead."
        )

    def get_success_message(self):
        return (
            f"New lead #{self.object.id} created successfully! "
            f"Agent {self.object.agent.user.name} will contact you soon."
        )

    def handle_integrity_error(self, error, form):
        messages.error(
            self.request,
            "This lead could not be created due to a system error. "
            "Our team has been notified.",
            extra_tags='alert-danger'
        )
        logger.error(f"Lead creation integrity error: {str(error)}", exc_info=True)
        return self.form_invalid(form)



class FavoriteDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        favorite = get_object_or_404(
            FavoriteProperty, pk=kwargs['pk'], 
            user=request.user
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
            messages.success(self.request, "✅ Subscribed successfully to property alerts.")
        else:
            messages.info(self.request, "ℹ️ You’re already subscribed to this preference.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "❌ There was an error with your subscription. Please try again.")
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
    

class LeadListView(LoginRequiredMixin, ListView):
    model = Lead
    template_name = "pages/property/lead_list.html"
    context_object_name = "leads"
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user

        # Ensure the user has an agent profile
        agent_profile = getattr(user, "agent_profile", None)
        if not agent_profile:
            messages.error(self.request, "No agent profile found.")
            return Lead.objects.none()

        # Filter leads by properties that belong to this agent
        queryset = Lead.objects.filter(
            property_link__agent=agent_profile
        ).select_related(
            "user", "property_link", "property_link__agent__user", "scheduled_viewing"
        )

        # Optional: Filter by status
        status = self.request.GET.get("status")
        if status:
            queryset = queryset.filter(status=status)

        # Optional: Search by email or property title
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(user__email__icontains=search) |
                Q(property_link__title__icontains=search)
            )

        return queryset.order_by("-created_at")
   
  
class LeadDetailView(AgentApprovalRequiredMixin, DetailView):
    model = Lead
    template_name = "pages/property/lead_detail.html"
    pk_url_kwarg = "pk"

    def get_object(self, queryset=None):
        pk = self.kwargs.get(self.pk_url_kwarg)
        try:
            uuid_obj = uuid.UUID(str(pk))
        except (ValueError, AttributeError):
            raise Http404("Invalid lead ID format")

        queryset = self.get_queryset()
        try:
            obj = queryset.get(id=uuid_obj)
        except (Lead.DoesNotExist, ValidationError):
            raise Http404("Lead not found or access denied")
        return obj

    def get_queryset(self):
        qs = super().get_queryset()
        if hasattr(self.request.user, 'agent_profile'):
            return qs.filter(property_link__agent=self.request.user.agent_profile)
        return qs.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = Lead_Status_Choices.choices
        return context

class LeadUpdateView(LoginRequiredMixin, UpdateView):
    model = Lead
    form_class = LeadCreateForm
    template_name = "pages/property/lead_update.html"
    pk_url_kwarg = "pk"

    def get_queryset(self):
        return super().get_queryset().filter(
            agent=self.request.user.agent_profile
        ).select_related("property_link", "user")

    def form_valid(self, form):
        messages.success(self.request, "Lead updated successfully")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("property:lead_detail", kwargs={"pk": self.object.pk})
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["property"] = self.object.property_link
        return context
    

class ViewingScheduleView(AgentApprovalRequiredMixin, CreateView):
    model = PropertyViewing
    form_class = ViewingScheduleForm
    template_name = "pages/property/viewing_schedule.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.lead = get_object_or_404(
            Lead,
            pk=kwargs["pk"],
            agent=request.user.agent_profile
        )
        # Store the lead ID in the view instance
        self.lead_id = kwargs["pk"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lead'] = self.lead
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
