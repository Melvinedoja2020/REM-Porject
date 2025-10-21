from django.contrib import messages
from django.contrib import messages as django_messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic import View, DeleteView

from core.applications.notifications.forms import MessageForm
from core.applications.notifications.forms import ReplyForm
from core.applications.notifications.models import Message
from core.applications.notifications.models import Notification
from core.helper.enums import NotificationType
from core.utils.utils import create_notification

# Create your views here.


# views.py


class MessageListView(LoginRequiredMixin, ListView):
    model = Message
    template_name = "pages/notifications/message_list.html"
    context_object_name = "messages"
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user

        # Only messages where this user is either sender or receiver
        queryset = (
            Message.objects.filter(Q(sender=user) | Q(receiver=user))
            .select_related("sender", "receiver", "property")
            .order_by("-created_at")
            .distinct()
        )

        # Mark only unread messages *received* by this user as read
        unread_messages = queryset.filter(receiver=user, is_read=False)
        if unread_messages.exists():
            unread_messages.update(is_read=True)

        return queryset


class MessageDetailView(LoginRequiredMixin, View):
    def get(self, request, pk, *args, **kwargs):
        message = get_object_or_404(Message, pk=pk)

        if request.user not in [message.sender, message.receiver]:
            django_messages.error(
                request,
                "You don't have permission to view this message.",
            )
            return redirect("notification:message_list")

        if message.receiver == request.user:
            message.mark_as_read()

        form = ReplyForm()
        return render(
            request,
            "pages/notifications/message_detail.html",
            {
                "message": message,
                "form": form,
                "replies": message.replies.all().order_by("created_at"),
            },
        )

    def post(self, request, pk, *args, **kwargs):
        message = get_object_or_404(Message, pk=pk)

        if request.user not in [message.sender, message.receiver]:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": False,
                        "error": "You don't have permission to view this message.",
                    },
                    status=403,
                )
            django_messages.error(
                request,
                "You don't have permission to view this message.",
            )
            return redirect("notification:message_list")

        form = ReplyForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.sender = request.user
            reply.receiver = (
                message.sender if request.user == message.receiver else message.receiver
            )
            reply.parent_message = message
            reply.property = message.property
            reply.save()

            # Create notification
            create_notification(
                user=reply.receiver,
                notification_type=NotificationType.MESSAGE,
                title=f"New message from {getattr(reply.sender, 'get_full_name', lambda: reply.sender.username)()}",
                message=reply.message,
                property=reply.property,
                extra_data={"message_id": str(reply.id)},
                link=request.build_absolute_uri(
                    reverse("notification:message_detail", kwargs={"pk": message.pk}),
                ),
            )

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                # Get profile picture URL
                profile_picture = ""
                if hasattr(request.user, "profile"):
                    profile_picture = request.user.profile.get_profile_picture()
                elif hasattr(request.user, "agent_profile"):
                    profile_picture = request.user.agent_profile.get_profile_picture()

                return JsonResponse(
                    {
                        "success": True,
                        "sender_name": getattr(
                            reply.sender,
                            "get_full_name",
                            lambda: reply.sender.username,
                        )(),
                        "sender_avatar": profile_picture,
                        "message_content": reply.message,
                        "created_at": reply.created_at.strftime("%b %d, %Y %H:%M"),
                    },
                )

            django_messages.success(request, "Your reply has been sent.")
            return redirect("notification:message_detail", pk=message.pk)

        # Form is invalid
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "success": False,
                    "error": "Invalid form data",
                    "errors": form.errors.get_json_data(),
                },
                status=400,
            )

        return render(
            request,
            "pages/notifications/message_detail.html",
            {
                "message": message,
                "form": form,
                "replies": message.replies.all().order_by("created_at"),
            },
        )


class MessageCreateView(LoginRequiredMixin, CreateView):
    model = Message
    form_class = MessageForm
    template_name = "pages/notifications/message_form.html"
    success_url = reverse_lazy("notification:message_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["sender"] = self.request.user

        # If this is a GET request and receiver_id is in kwargs
        if self.request.method == "GET" and "receiver_id" in self.kwargs:
            initial = kwargs.get("initial", {})
            initial["receiver"] = self.kwargs["receiver_id"]
            kwargs["initial"] = initial

        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # If receiver_id is provided, get the agent's profile
        if "receiver_id" in self.kwargs:
            from core.applications.users.models import AgentProfile

            try:
                agent = AgentProfile.objects.get(user_id=self.kwargs["receiver_id"])
                context["recipient"] = agent
                context["title"] = f"Message {agent.user.name}"
            except AgentProfile.DoesNotExist:
                pass

        return context

    def form_valid(self, form):
        form.instance.sender = self.request.user
        django_messages.success(self.request, "Your message has been sent.")
        return super().form_valid(form)

class MessageDeleteView(LoginRequiredMixin, DeleteView):
    model = Message
    template_name = "pages/notifications/message_confirm_delete.html"
    context_object_name = "message"
    success_url = reverse_lazy("notification:message_list")

    def dispatch(self, request, *args, **kwargs):
        """
        Ensure only the sender or receiver can delete this message.
        """
        message = self.get_object()
        if message.sender != request.user and message.receiver != request.user:
            messages.error(request, "You don't have permission to delete this message.")
            return redirect("notification:message_list")
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        """
        Override delete to add success message.
        """
        messages.success(request, "Message deleted successfully.")
        return super().delete(request, *args, **kwargs)

class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    context_object_name = "notifications"
    template_name = "pages/notifications/notification_list.html"
    paginate_by = 20  # optional

    def get_queryset(self):
        return Notification.objects.filter(
            user=self.request.user,
        )


class NotificationDetailView(LoginRequiredMixin, DetailView):
    model = Notification
    context_object_name = "notification"
    template_name = "pages/notifications/notification_detail.html"

    def get_queryset(self):
        return Notification.objects.filter(
            user=self.request.user,
        )

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        if not self.object.is_read:
            self.object.is_read = True
            self.object.save(update_fields=["is_read"])

        # Optional: Redirect if link is provided
        if self.object.link:
            return redirect(self.object.link)

        return super().get(request, *args, **kwargs)


class MarkAllNotificationsReadView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        notifications = Notification.objects.filter(
            user=request.user,
            is_read=False,
        )
        notifications.update(is_read=True)
        messages.success(request, "All notifications marked as read.")
        return redirect("notifications:list")


class NotificationDeleteView(LoginRequiredMixin, DeleteView):
    model = Notification
    template_name = "notifications/notification_confirm_delete.html"
    success_url = reverse_lazy("notification:notification_list")

    def test_func(self):
        """
        Ensure the logged-in user owns this notification.
        """
        notification = self.get_object()
        return notification.user == self.request.user

    def delete(self, request, *args, **kwargs):
        """
        Override delete to add a success message.
        """
        response = super().delete(request, *args, **kwargs)
        messages.success(request, "Notification deleted successfully.")
        return response


class MarkNotificationReadView(View):
    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        notification.is_read = True
        notification.save()
        messages.success(request, "Notification marked as read.")
        return redirect(
            request.headers.get("referer", "notification:notification_list")
        )
