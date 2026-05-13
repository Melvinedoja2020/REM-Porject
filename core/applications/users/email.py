from templated_mail.mail import BaseEmailMessage

from core.applications.users.token import default_token_generator
from core.helpers.emails import build_email_context


class ActivationEmail(BaseEmailMessage):
    template_name = "email/activation.html"

    def get_context_data(self):
        # ActivationEmail can be deleted
        context = super().get_context_data()
        user = context.get("user")
        context["token"] = default_token_generator.make_token(user)
        return build_email_context(context)


class ConfirmationEmail(BaseEmailMessage):
    template_name = "email/confirmation.html"

    def get_context_data(self):
        return build_email_context(super().get_context_data())


class PasswordResetEmail(ActivationEmail):
    template_name = "email/password_reset.html"

    def get_context_data(self):
        return build_email_context(super().get_context_data())


class PasswordChangedConfirmationEmail(BaseEmailMessage):
    template_name = "email/password_changed_confirmation.html"

    def get_context_data(self):
        return build_email_context(super().get_context_data())


class UsernameChangedConfirmationEmail(BaseEmailMessage):
    template_name = "email/username_changed_confirmation.html"

    def get_context_data(self):
        return build_email_context(super().get_context_data())


class UsernameResetEmail(ActivationEmail):
    template_name = "email/username_reset.html"

    def get_context_data(self):
        context = super().get_context_data()

        user = context.get("user")
        context["token"] = default_token_generator.make_token(user)
        return build_email_context(context)
