from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, ListView, View, DetailView

from core.applications.notifications.forms import MessageForm, ReplyForm
from core.applications.notifications.models import Message
from django.contrib import messages as django_messages
from django.db.models import Q

from core.utils.utils import create_notification
from core.helper.enums import NotificationType

# Create your views here.


# views.py



class MessageListView(LoginRequiredMixin, ListView):
    model = Message
    template_name = 'pages/notifications/message_list.html'
    context_object_name = 'messages'
    ordering = ['-created_at']

    def get_queryset(self):
        # Only messages sent or received by the user
        queryset = Message.objects.filter(
            Q(sender=self.request.user) | Q(receiver=self.request.user)
        ).order_by('-created_at')

        # Mark unread received messages as read
        Message.objects.filter(receiver=self.request.user, is_read=False).update(is_read=True)
        
        return queryset


class MessageDetailView(LoginRequiredMixin, View):
    def get(self, request, pk, *args, **kwargs):
        message = get_object_or_404(Message, pk=pk)

        if request.user not in [message.sender, message.receiver]:
            django_messages.error(request, "You don't have permission to view this message.")
            return redirect('notification:message_list')

        if message.receiver == request.user:
            message.mark_as_read()

        form = ReplyForm()
        return render(request, 'pages/notifications/message_detail.html', {
            'message': message,
            'form': form,
            'replies': message.replies.all().order_by('created_at')
        })

    def post(self, request, pk, *args, **kwargs):
        message = get_object_or_404(Message, pk=pk)

        if request.user not in [message.sender, message.receiver]:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': "You don't have permission to view this message."
                }, status=403)
            django_messages.error(request, "You don't have permission to view this message.")
            return redirect('notification:message_list')

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
                extra_data={'message_id': str(reply.id)},
                link=request.build_absolute_uri(
                    reverse('notification:message_detail', kwargs={'pk': message.pk})
                )
            )

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Get profile picture URL
                profile_picture = ''
                if hasattr(request.user, 'profile'):
                    profile_picture = request.user.profile.get_profile_picture()
                elif hasattr(request.user, 'agent_profile'):
                    profile_picture = request.user.agent_profile.get_profile_picture()
                
                return JsonResponse({
                    'success': True,
                    'sender_name': getattr(reply.sender, 'get_full_name', lambda: reply.sender.username)(),
                    'sender_avatar': profile_picture,
                    'message_content': reply.message,
                    'created_at': reply.created_at.strftime("%b %d, %Y %H:%M")
                })

            django_messages.success(request, "Your reply has been sent.")
            return redirect('notification:message_detail', pk=message.pk)

        # Form is invalid
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': 'Invalid form data',
                'errors': form.errors.get_json_data()
            }, status=400)

        return render(request, 'pages/notifications/message_detail.html', {
            'message': message,
            'form': form,
            'replies': message.replies.all().order_by('created_at')
        })


class MessageCreateView(LoginRequiredMixin, CreateView):
    model = Message
    form_class = MessageForm
    template_name = 'pages/notifications/message_form.html'
    success_url = reverse_lazy('notification:message_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['sender'] = self.request.user
        
        # If this is a GET request and receiver_id is in kwargs
        if self.request.method == 'GET' and 'receiver_id' in self.kwargs:
            initial = kwargs.get('initial', {})
            initial['receiver'] = self.kwargs['receiver_id']
            kwargs['initial'] = initial
            
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # If receiver_id is provided, get the agent's profile
        if 'receiver_id' in self.kwargs:
            from core.applications.users.models import AgentProfile
            try:
                agent = AgentProfile.objects.get(user_id=self.kwargs['receiver_id'])
                context['recipient'] = agent
                context['title'] = f"Message {agent.user.name}"
            except AgentProfile.DoesNotExist:
                pass
                
        return context

    def form_valid(self, form):
        form.instance.sender = self.request.user
        django_messages.success(self.request, "Your message has been sent.")
        return super().form_valid(form)
