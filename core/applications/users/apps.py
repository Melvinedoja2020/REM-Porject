import contextlib

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.applications.users"

    def ready(self):
        try:
            import core.applications.users.signals  # noqa F401
        except ImportError:
            pass
