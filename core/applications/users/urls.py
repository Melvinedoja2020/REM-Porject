from django.urls import path

from core.applications.users.forms import UserSignupForm


from .views import (
    AgentDashboardView, AgentProfileView, OwnerProfileView, 
    SuperUserSignupView, UserProfileView, UserDashboardView, 
    user_detail_view
)
from .views import user_redirect_view
from .views import user_update_view
from allauth.account.views import SignupView

app_name = "users"
urlpatterns = [
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("<int:pk>/", view=user_detail_view, name="detail"),
    #  signup urls for different user types
    path(
        "signup/user/", SignupView.as_view(form_class=UserSignupForm, 
        template_name="account/signup_user.html"), name="user_signup"
    ),
    
    # profile urls for different user types
    path("profile/user/<int:pk>/", UserProfileView.as_view(), name="user_profile"),
    path("profile/agent/<int:pk>/", AgentProfileView.as_view(), name="agent_profile"),
    path("profile/owner/<int:pk>/", OwnerProfileView.as_view(), name="owner_profile"),

    path("dashboard/agent", AgentDashboardView.as_view(), name="agent_dashboard"),
    path("dashboard/user", UserDashboardView.as_view(), name="user_dashboard"),


    path("superuser/", SuperUserSignupView.as_view(), name="superuser_signup"),
]
