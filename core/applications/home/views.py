from django.shortcuts import render
from django.views.generic import TemplateView, ListView, DetailView

from core.applications.property.forms import PropertySearchForm
from core.applications.property.models import Property
from core.applications.users.models import AgentProfile
from core.helper.enums import PropertyListingType
from django.db.models import Q
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
        """
        Returns a queryset of available properties for rent.
        Filters the properties based on the search criteria provided in the GET request.
        """
        queryset = Property.objects.filter(
            is_available=True,
            property_listing=PropertyListingType.RENT,
        ).select_related("agent").prefetch_related("images", "amenities")

        form = PropertySearchForm(self.request.GET)

        if form.is_valid():
            cd = form.cleaned_data

            q = cd.get("q")
            if q:
                queryset = queryset.filter(
                    Q(title__icontains=q) | Q(description__icontains=q)
                )

            if cd.get("location"):
                queryset = queryset.filter(location__icontains=cd["location"])

            if cd.get("property_type"):
                queryset = queryset.filter(property_type=cd["property_type"])

            if cd.get("min_price"):
                queryset = queryset.filter(price__gte=cd["min_price"])

            if cd.get("max_price"):
                queryset = queryset.filter(price__lte=cd["max_price"])

            if cd.get("min_bedrooms"):
                queryset = queryset.filter(bedrooms__gte=cd["min_bedrooms"])

            if cd.get("min_bathrooms"):
                queryset = queryset.filter(bathrooms__gte=cd["min_bathrooms"])

            if cd.get("amenities"):
                for amenity in cd["amenities"]:
                    queryset = queryset.filter(amenities=amenity)

        return queryset.order_by("-created_at").distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = PropertySearchForm(self.request.GET)
        context["page_title"] = "Rent Properties"
        return context


class RentPropertyDetailView(DetailView):
    model = Property
    template_name = "pages/property/property_detail.html"
    context_object_name = "property"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return (
            Property.objects.select_related("agent")
            .prefetch_related("images", "amenities")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        property = self.get_object()

        # Basic "similar" logic: same location and property type, excluding the current property
        context["similar_properties"] = (
            Property.objects.filter(
                (
                    Q(location__icontains=property.location) |
                    Q(property_type=property.property_type)
                ),
                is_available=True
            )
            .exclude(id=property.id)
            .order_by("?")[:3]
        )

        return context