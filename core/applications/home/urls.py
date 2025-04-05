from django.urls import path

from core.applications.home.views import HomeView



app_name = "home"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),  
]
