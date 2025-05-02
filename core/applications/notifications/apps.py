from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    name = "core.applications.notifications"

    
    def ready(self):
        try:
            import core.applications.notifications.signals  # noqa F401
        except ImportError:
            pass
