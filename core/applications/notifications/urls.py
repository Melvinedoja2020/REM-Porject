from django.urls import path

from core.applications.notifications.views import (
    MarkAllNotificationsReadView,
    MarkNotificationReadView,
    NotificationDeleteView,
)
from core.applications.notifications.views import MessageCreateView
from core.applications.notifications.views import MessageDetailView
from core.applications.notifications.views import MessageListView
from core.applications.notifications.views import NotificationDetailView
from core.applications.notifications.views import NotificationListView, MessageDeleteView
from django.views.generic import RedirectView

app_name = "notification"

urlpatterns = [
    # Messages
    path("messages/send/", MessageCreateView.as_view(), name="send_message"),
    path("messages/", MessageListView.as_view(), name="message_list"),
    path(
        "message/create/<int:receiver_id>/",
        MessageCreateView.as_view(),
        name="message_create_to_agent",
    ),
    path("messages/delete/<str:pk>/", MessageDeleteView.as_view(), name="message_delete"),
    path("messages/<str:pk>/", MessageDetailView.as_view(), name="message_detail"),
    path("messages/<str:pk>/reply/", MessageDetailView.as_view(), name="send_reply"),
    path("notifications", NotificationListView.as_view(), name="notification_list"),
    path("<str:pk>/", NotificationDetailView.as_view(), name="notification_detail"),
    path(
        "delete/<str:pk>/", NotificationDeleteView.as_view(), name="notification_delete"
    ),
    path(
        "notifications/<str:pk>/mark-read/",
        MarkNotificationReadView.as_view(),
        name="notification_mark_read",
    ),
    path(
        "mark-all-read/",
        MarkAllNotificationsReadView.as_view(),
        name="mark_all_read",
    ),
    path("favicon.ico", RedirectView.as_view(url="/static/favicon.ico")),
]
