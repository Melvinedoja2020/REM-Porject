from django.urls import path

from core.applications.notifications.views import (
    MessageCreateView, MessageListView, MessageDetailView,
    NotificationListView, NotificationDetailView,
    MarkAllNotificationsReadView
    
)


app_name = "notification"

urlpatterns = [
    # Messages
    path("messages/send/", MessageCreateView.as_view(), name="send_message"),
    path("messages/", MessageListView.as_view(), name="message_list"),
    path('message/create/<int:receiver_id>/', MessageCreateView.as_view(), name='message_create_to_agent'),
    path("messages/<uuid:pk>/", MessageDetailView.as_view(), name="message_detail"),
    path('messages/<uuid:pk>/reply/', MessageDetailView.as_view(), name='send_reply'),

    path("", NotificationListView.as_view(), name="list"),
    path("<int:pk>/", NotificationDetailView.as_view(), name="notification_detail"),
    path("mark-all-read/", MarkAllNotificationsReadView.as_view(), name="mark_all_read"),
]