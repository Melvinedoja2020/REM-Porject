from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.shortcuts import redirect
from django.contrib import messages


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    A generic mixin to restrict views to specific user roles.
    Example usage:
        class SomeView(RoleRequiredMixin, View):
            required_role = UserRoleChoice.AGENT
    """

    required_role = None

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == self.required_role
    
    def handle_no_permission(self):
        return redirect("dashboard:home")


class AgentApprovalRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        print("🔥 AgentApprovalRequiredMixin dispatch called")
        if hasattr(request.user, "agent_profile") and not request.user.agent_profile.verified:
            messages.warning(
                request, 
                "Your agent profile is pending approval you will have access once approved."
            )
            return redirect("home:home")
        return super().dispatch(request, *args, **kwargs)



class AgentRequiredMixin(LoginRequiredMixin):
    """Verify that the current user is an agent"""
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request.user, 'agentprofile'):
            messages.error(request, "This section is for agents only")
            return redirect('home:home')
        return super().dispatch(request, *args, **kwargs)
