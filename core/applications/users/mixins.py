# users/mixins.py
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib import messages
from django.shortcuts import redirect

class RoleRequiredMixin(UserPassesTestMixin):
    required_role = None
    error_message = "You are not authorized to access this page."

    def test_func(self):
        return self.request.user.role == self.required_role

    def handle_no_permission(self):
        messages.error(self.request, self.error_message)
        return redirect("users:choose_role")  # Customize this redirect as needed
