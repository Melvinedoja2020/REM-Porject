# notifications/utils.py
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings

from core.applications.notifications.models import Notification, NotificationPreference


def create_notification(user, notification_type, title, message, **kwargs):
    """
    Creates and sends a notification to a user
    """
    # Get or create user preferences
    pref, _ = NotificationPreference.objects.get_or_create(user=user)
    
    # Check if user wants this type of notification
    if not getattr(pref, f"{notification_type}_notifications", True):
        return None
    
    # Create the notification
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        related_property=kwargs.get('property'),
        related_message=kwargs.get('message'),
        metadata=kwargs.get('metadata', {})
    )
    
    # Send email if enabled
    if pref.email_enabled:
        send_notification_email(notification)
    
    # Send push notification if enabled (would integrate with your push service)
    if pref.push_enabled:
        send_push_notification(notification)
    
    return notification

def send_notification_email(notification):
    subject = f"{settings.SITE_NAME} - {notification.title}"
    context = {
        'notification': notification,
        'site_name': settings.SITE_NAME,
        'site_url': settings.SITE_URL
    }
    
    html_message = render_to_string('pages/notifications/email_notification.html', context)
    text_message = render_to_string('pages/notifications/email_notification.txt', context)
    
    send_mail(
        subject,
        text_message,
        settings.DEFAULT_FROM_EMAIL,
        [notification.user.email],
        html_message=html_message,
        fail_silently=True
    )

def send_push_notification(notification):
    # Implementation would depend on your push notification service
    # (Firebase, OneSignal, etc.)
    pass