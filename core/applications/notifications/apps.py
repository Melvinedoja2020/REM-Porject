import contextlib

from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    name = "core.applications.notifications"

    def ready(self):
        with contextlib.suppress(ImportError):
            import core.applications.notifications.signals  # noqa: F401
