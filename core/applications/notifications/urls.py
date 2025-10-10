from django.urls import path

from core.applications.notifications.views import MarkAllNotificationsReadView
from core.applications.notifications.views import MessageCreateView
from core.applications.notifications.views import MessageDetailView
from core.applications.notifications.views import MessageListView
from core.applications.notifications.views import NotificationDetailView
from core.applications.notifications.views import NotificationListView
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
    path("messages/<str:pk>/", MessageDetailView.as_view(), name="message_detail"),
    path("messages/<str:pk>/reply/", MessageDetailView.as_view(), name="send_reply"),
    path("notifications", NotificationListView.as_view(), name="notification_list"),
    path("<str:pk>/", NotificationDetailView.as_view(), name="notification_detail"),
    path(
        "mark-all-read/",
        MarkAllNotificationsReadView.as_view(),
        name="mark_all_read",
    ),
    path("favicon.ico", RedirectView.as_view(url="/static/favicon.ico")),
]
