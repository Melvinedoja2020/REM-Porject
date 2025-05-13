from django.shortcuts import get_object_or_404, render
from django.views.generic import TemplateView, ListView, DetailView

from core.applications.home.forms import ContactForm
from core.applications.property.forms import PropertySearchForm
from core.applications.property.models import FavoriteProperty, Property, PropertyImage
from core.applications.users.models import AgentProfile
from core.helper.enums import PropertyListingType
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from django.core.mail import send_mail
from django.contrib import messages
from django.conf import settings
from django.views.generic.edit import FormView
from django.urls import reverse_lazy
from django.core.mail import EmailMessage
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


class ContactUsView(FormView):
    template_name = "pages/contact.html"
    form_class = ContactForm
    success_url = reverse_lazy("contact")

    def form_valid(self, form):
        name = form.cleaned_data['name']
        email = form.cleaned_data['email']
        subject = form.cleaned_data['subject']
        message = form.cleaned_data['message']

        full_message = f"Message from {name} <{email}>:\n\n{message}"

        email_message = EmailMessage(
            subject=subject,
            body=full_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.CONTACT_EMAIL],
            reply_to=[email]  # This ensures the admin can reply directly to the user
        )
        email_message.send()

        messages.success(self.request, 'Your message has been sent successfully.')
        return super().form_valid(form)
    

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


class PropertyDetailView(DetailView):
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
        if self.request.user.is_authenticated:
            context["favorite_property_ids"] = list(
                FavoriteProperty.objects.filter(user=self.request.user)
                .values_list("property_id", flat=True)
            )
        else:
            context["favorite_property_ids"] = []
        return context

class PropertyGalleryView(ListView):
    """
    A class-based view to display a gallery of images for a specific property.
    Implements pagination, template rendering, and context enhancement.
    """
    model = PropertyImage
    template_name = "pages/property/gallery.html"
    context_object_name = "images"
    paginate_by = 12  # Show 12 images per page
    
    def get_queryset(self):
        """
        Override the default queryset to filter images for the specified property.
        """
        self.property = get_object_or_404(
            Property, 
            pk=self.kwargs["property_id"]
        )
        return super().get_queryset().filter(
            property=self.property
        ).order_by("-created_at")  # Show newest first
    
    def get_context_data(self, **kwargs):
        """
        Add the property object to the template context.
        """
        context = super().get_context_data(**kwargs)
        context["property"] = self.property
        context["page_title"] = f"Photo Gallery - {self.property.title}"
        return context



class AgentListView(LoginRequiredMixin, ListView):
    model = AgentProfile
    template_name = "pages/agents/agent_list.html"
    context_object_name = "agents"
    paginate_by = 2

    def get_queryset(self):
        return (
            AgentProfile.objects
            .filter(verified=True)
            .select_related("user")  # load user object
            .prefetch_related("user__social_media_links")  # load social links
            .order_by("-rating")
        )

     
class AgentDetailView(LoginRequiredMixin, DetailView):
    model = AgentProfile
    template_name = "pages/agents/agent_detail.html"
    context_object_name = "agent"

    def get_object(self):
        return get_object_or_404(AgentProfile, pk=self.kwargs.get("id"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        agent = self.get_object()
        properties = agent.properties.filter(is_available=True)

        paginator = Paginator(properties, 2)
        page_number = self.request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        context.update({
            "properties": page_obj,
            "property_count": properties.count()
        })
        return context

    def post(self, request, *args, **kwargs):
        agent = self.get_object()
        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        message = request.POST.get("message")

        full_message = f"""
        You received a message from a user on your agent profile page:
        
        Name: {name}
        Email: {email}
        Phone: {phone}
        
        Message:
        {message}
        """

        try:
            send_mail(
                subject=f"New inquiry from {name}",
                message=full_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[agent.user.email],  # Assuming AgentProfile has OneToOne to User
            )
            messages.success(request, "Your message has been sent successfully.")
        except Exception as e:
            messages.error(request, "An error occurred while sending your message. Please try again.")

        return self.get(request, *args, **kwargs)
    

# Needed for AJAX without CSRF token (or add token client-side)
@method_decorator(csrf_exempt, name="dispatch")
class ToggleFavoriteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        property_id = request.POST.get("property_id")
        property_obj = get_object_or_404(Property, pk=property_id)

        favorite, created = FavoriteProperty.objects.get_or_create(
            user=request.user,
            property=property_obj,
        )

        if not created:
            favorite.delete()
            return JsonResponse({"status": "removed"})
        return JsonResponse({"status": "added"})


class FavoriteCountAPI(LoginRequiredMixin, View):
    def get(self, request):
        return JsonResponse({
            'count': request.user.favorites.count()
        })