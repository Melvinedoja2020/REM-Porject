from django.shortcuts import render
from django.views.generic import TemplateView, ListView, DetailView

from core.applications.property.models import Property
from core.applications.users.models import AgentProfile
from core.helper.enums import PropertyListingType
# Create your views here.



class HomeView(TemplateView):
    template_name = "pages/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["properties"] = Property.objects.filter(
            is_available=True
        ).order_by("-created_at")[:6]
        context["agents_profile"] = AgentProfile.objects.filter(
            verified=True
        )
        return context


class RentPropertyListView(ListView):
    model = Property
    template_name = "pages/property/property_list.html"
    context_object_name = "properties"
    paginate_by = 6

    def get_queryset(self):
        return (
            Property.objects.filter(
                is_available=True,
                property_listing=PropertyListingType.RENT,
            )
            .select_related("agent", "property_type")
            .prefetch_related("images", "amenities")
            .order_by("-created_at")
        )


class RentPropertyDetailView(DetailView):
    model = Property
    template_name = "pages/property/property_detail.html"
    context_object_name = "property"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return (
            Property.objects.select_related("agent", "property_type")
            .prefetch_related("images", "amenities")
        )