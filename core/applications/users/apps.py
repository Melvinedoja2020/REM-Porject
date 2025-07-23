from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.applications.users"

    def ready(self):
        try:
            import core.applications.users.signals  # noqa F401
        except ImportError:
            pass
