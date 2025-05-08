from django.urls import path

from core.applications.notifications.views import (
    MessageCreateView, MessageListView, MessageDetailView
    
)


app_name = "notification"

urlpatterns = [
    # Messages
    path("messages/send/", MessageCreateView.as_view(), name="send_message"),
    path("messages/", MessageListView.as_view(), name="message_list"),
    path('message/create/<int:receiver_id>/', MessageCreateView.as_view(), name='message_create_to_agent'),
    path("messages/<uuid:pk>/", MessageDetailView.as_view(), name="message_detail"),
    path('messages/<uuid:pk>/reply/', MessageDetailView.as_view(), name='send_reply'),
]