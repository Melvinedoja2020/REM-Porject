from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.generic import (
    CreateView, UpdateView, ListView, DetailView, DeleteView
)

from core.applications.property.forms import LeadForm, PropertyForm, PropertyImageForm
from core.applications.property.models import FavoriteProperty, Lead, Property, PropertyImage, PropertyType
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.shortcuts import redirect

from core.helper.enums import PropertyListingType, UserRoleChoice
from core.helper.mixins import AgentApprovalRequiredMixin
from django.views import View
# Create your views here.



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
        new_property_type = form.cleaned_data.get('new_property_type')
        if new_property_type:
            property_type = PropertyType.objects.filter(title__iexact=new_property_type).first()
            if not property_type:
                property_type = PropertyType.objects.create(title=new_property_type)
            form.instance.property_type = property_type

        # Reassign agent only if it's not set
        if not form.instance.agent:
            form.instance.agent = self.request.user.agent_profile

        response = super().form_valid(form)

        # Handle additional images if uploaded
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
        return image.property.agent == self.request.user.agentprofile

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


class LeadCreateView(CreateView):
    model = Lead
    form_class = LeadForm
    template_name = "lead_form.html"
    success_url = reverse_lazy("lead_list")


class LeadListView(ListView):
    model = Lead
    template_name = "lead_list.html"
    context_object_name = "leads"


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
    

class FavoriteDeleteView(LoginRequiredMixin, DeleteView):
    model = FavoriteProperty
    template_name = "pages/dashboard/favorite_delete.html"
    success_url = reverse_lazy("property:customers_favorite_list")
    
    