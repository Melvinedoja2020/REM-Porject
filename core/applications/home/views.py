from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import EmailMessage
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic import TemplateView
from django.views.generic.edit import FormView

from core.applications.home.forms import ContactForm
from core.applications.property.models import FavoriteProperty
from core.applications.property.models import Property
from core.applications.property.models import PropertyImage
from core.applications.users.models import AgentProfile
from core.helper.enums import PropertyListingType
from core.helper.enums import PropertyTypeChoices
from core.helper.mixins import PropertySearchMixin

# Create your views here.


class HomeView(TemplateView):
    template_name = "pages/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["properties"] = Property.objects.available().featured_first()[:6]
        context["agents_profile"] = AgentProfile.objects.filter(verified=True)
        context["property_types"] = PropertyTypeChoices.choices
        return context


class ContactUsView(FormView):
    template_name = "pages/contact.html"
    form_class = ContactForm
    success_url = reverse_lazy("contact")

    def form_valid(self, form):
        name = form.cleaned_data["name"]
        email = form.cleaned_data["email"]
        subject = form.cleaned_data["subject"]
        message = form.cleaned_data["message"]

        full_message = f"Message from {name} <{email}>:\n\n{message}"

        email_message = EmailMessage(
            subject=subject,
            body=full_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.CONTACT_EMAIL],
            reply_to=[email],  # This ensures the admin can reply directly to the user
        )
        email_message.send()

        messages.success(self.request, "Your message has been sent successfully.")
        return super().form_valid(form)


class PropertyListView(PropertySearchMixin, ListView):
    model = Property
    template_name = "pages/property/property_list.html"
    context_object_name = "properties"
    paginate_by = 6

    def get_queryset(self):
        base_queryset = (
            Property.objects.filter(
                is_available=True,
            )
            .select_related("agent")
            .prefetch_related("images", "amenities")
        )

        return self.get_filtered_queryset(base_queryset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Rent Properties"
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            html = render_to_string(
                "partials/_property_list.html",
                context,
                request=self.request,
            )
            return JsonResponse({"html": html})
        return super().render_to_response(context, **response_kwargs)


class RentPropertyListView(PropertySearchMixin, ListView):
    model = Property
    template_name = "pages/property/property_list.html"
    context_object_name = "properties"
    paginate_by = 6

    def get_queryset(self):
        """"""
        base_queryset = (
            Property.objects.available()
            .filter(property_listing=PropertyListingType.RENT)
            .featured_first()
            .select_related("agent")
            .prefetch_related("images", "amenities")
        )
        return self.get_filtered_queryset(base_queryset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Rent Properties"
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            html = render_to_string(
                "partials/_property_list.html",
                context,
                request=self.request,
            )
            return JsonResponse({"html": html})
        return super().render_to_response(context, **response_kwargs)


class BuyPropertyListView(PropertySearchMixin, ListView):
    model = Property
    template_name = "pages/property/property_list.html"
    context_object_name = "properties"
    paginate_by = 6

    def get_queryset(self):
        base_queryset = (
            Property.objects.available()
            .filter(property_listing=PropertyListingType.FOR_SALE)
            .featured_first()
            .select_related("agent")
            .prefetch_related("images", "amenities")
        )
        return self.get_filtered_queryset(base_queryset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Rent Properties"
        return context

    def render_to_response(self, context, **response_kwargs):
        """
        Render the response, returning JSON for AJAX requests.
        """
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            html = render_to_string(
                "partials/_property_list.html",
                context,
                request=self.request,
            )
            return JsonResponse({"html": html})
        return super().render_to_response(context, **response_kwargs)


class PropertyDetailView(DetailView):
    model = Property
    template_name = "pages/property/property_detail.html"
    context_object_name = "property"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Property.objects.select_related("agent").prefetch_related(
            "images",
            "amenities",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        property = self.get_object()

        # Basic "similar" logic: same location and property type, excluding the current property
        context["similar_properties"] = (
            Property.objects.filter(
                (
                    Q(location__icontains=property.location)
                    | Q(property_type=property.property_type)
                ),
                is_available=True,
            )
            .exclude(id=property.id)
            .order_by("?")[:3]
        )
        if self.request.user.is_authenticated:
            context["favorite_property_ids"] = list(
                FavoriteProperty.objects.filter(user=self.request.user).values_list(
                    "property_id",
                    flat=True,
                ),
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
            pk=self.kwargs["property_id"],
        )
        return (
            super()
            .get_queryset()
            .filter(
                property=self.property,
            )
            .order_by("-created_at")
        )  # Show newest first

    def get_context_data(self, **kwargs):
        """
        Add the property object to the template context.
        """
        context = super().get_context_data(**kwargs)
        context["property"] = self.property
        context["page_title"] = f"Photo Gallery - {self.property.title}"
        return context


class PropertyTypeListView(PropertySearchMixin, ListView):
    model = Property
    template_name = "pages/property/property_list.html"
    context_object_name = "properties"
    paginate_by = 12

    def get_queryset(self):
        type_value = self.kwargs.get("type")
        try:
            PropertyTypeChoices(type_value)
        except ValueError:
            raise Http404("Invalid property type")

        base_queryset = (
            Property.objects.filter(
                property_type=type_value,
                is_available=True,
            )
            .select_related("agent")
            .prefetch_related("images", "amenities")
        )

        return self.get_filtered_queryset(base_queryset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        type_value = self.kwargs.get("type")
        context["property_type_label"] = PropertyTypeChoices(type_value).label
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            html = render_to_string(
                "partials/_property_list.html",
                context,
                request=self.request,
            )
            return JsonResponse({"html": html})
        return super().render_to_response(context, **response_kwargs)


class AgentListView(LoginRequiredMixin, ListView):
    model = AgentProfile
    template_name = "pages/agents/agent_list.html"
    context_object_name = "agents"
    paginate_by = 2

    def get_queryset(self):
        return (
            AgentProfile.objects.filter(verified=True)
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

        context.update(
            {
                "properties": page_obj,
                "property_count": properties.count(),
            },
        )
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
                recipient_list=[
                    agent.user.email,
                ],  # Assuming AgentProfile has OneToOne to User
            )
            messages.success(request, "Your message has been sent successfully.")
        except Exception:
            messages.error(
                request,
                "An error occurred while sending your message. Please try again.",
            )

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
        return JsonResponse(
            {
                "count": request.user.favorites.count(),
            },
        )
