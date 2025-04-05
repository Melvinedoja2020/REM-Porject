from django.shortcuts import render
from django.views.generic import TemplateView

from core.applications.property.models import Property
# Create your views here.



class HomeView(TemplateView):
    template_name = "pages/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["properties"] = Property.objects.filter(
            is_available=True
        ).order_by("-created_at")[:6]
        return context
