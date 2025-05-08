from django.apps import AppConfig
import contextlib


class PropertyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.applications.property'

    def ready(self):
        with contextlib.suppress(ImportError):
            import core.applications.notifications.signals
