import contextlib

from django.apps import AppConfig


class PropertyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.applications.property"

    def ready(self):
        with contextlib.suppress(ImportError):
            pass
