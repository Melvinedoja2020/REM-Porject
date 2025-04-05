from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.shortcuts import redirect


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