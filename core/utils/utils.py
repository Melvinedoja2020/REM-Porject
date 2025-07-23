import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import models
from django.template.loader import render_to_string
from django.urls import reverse

from core.applications.notifications.models import Notification
from core.applications.notifications.models import NotificationPreference
from core.applications.property.models import PropertySubscription
from core.helper.enums import NotificationType

logger = logging.getLogger(__name__)


def is_user_subscribed_for_property(user, property_obj):
    """
    Check if a user is subscribed to a property based on location containment and property type.
    """
    subscriptions = PropertySubscription.objects.filter(
        user=user,
    ).filter(
        models.Q(property_type=property_obj.property_type)
        | models.Q(property_type__isnull=True),
    )

    property_location = (property_obj.location or "").lower()

    for sub in subscriptions:
        sub_location = (sub.location or "").lower()
        if not sub_location or sub_location in property_location:
            return True

    return False


def create_notification(user, notification_type, title, message, **kwargs):
    """
    Create a notification and optionally send email and push if the user has those enabled.
    """
    pref, _ = NotificationPreference.objects.get_or_create(user=user)

    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        property=kwargs.get("property"),
        extra_data=kwargs.get("metadata", {}),
    )

    if pref.email_notifications:
        send_notification_email(notification)

    if pref.push_notifications:
        send_push_notification(notification)

    return notification


def send_notification_email(notification):
    """
    Send an email notification using rendered templates.
    """
    site_name = getattr(settings, "SITE_NAME", "Real Estate Market Place")
    site_url = settings.SITE_URL + reverse("notification:message_list")
    default_from_email = getattr(
        settings,
        "DEFAULT_FROM_EMAIL",
        "Real Estate <noreply@example.com>",
    )
    subject_prefix = getattr(settings, "EMAIL_SUBJECT_PREFIX", f"[{site_name}] ")

    subject = f"{subject_prefix}{notification.title or 'Notification'}"

    context = {
        "notification": notification,
        "site_name": site_name,
        "site_url": site_url,
    }

    html_message = render_to_string(
        "pages/notifications/email_notification.html",
        context,
    )
    text_message = render_to_string(
        "pages/notifications/email_notification.txt",
        context,
    )

    send_mail(
        subject=subject,
        message=text_message,
        from_email=default_from_email,
        recipient_list=[notification.user.email],
        html_message=html_message,
        fail_silently=True,
    )


def send_favorite_notifications(agent, user_email, property):
    message = (
        f"user with email {user_email} has favorited your listing: {property.title}"
    )
    # Add it to a notification system
    create_notification(
        user=agent.user,
        notification_type=NotificationType.FAVORITE,
        title="Property Favorited",
        message=message,
        property=property,
        metadata={"property_id": str(property.id)},  # Convert UUID to string
    )

    # You can also email the agent
    send_mail(
        subject="Your property was favorited",
        message=message,
        recipient_list=[agent.user.email],
        from_email=settings.DEFAULT_FROM_EMAIL,
    )


def send_push_notification(notification):
    """
    Placeholder for push notification logic.
    Implement based on your provider (e.g., Firebase, OneSignal).
    """


def process_new_lead(lead):
    print("Processing new lead<<<<>>>>>:", lead.id)

    try:
        if not hasattr(lead.agent.user, "agent_profile"):
            raise ValueError("Associated agent has no profile")

        if not hasattr(lead.user, "profile"):
            raise ValueError("Lead user has no profile")

        context = {
            "lead": lead,
            "agent": lead.agent.user.agent_profile,
            "user": lead.user.profile,
            "property": lead.property_link,
            "dashboard_url": getattr(
                settings,
                "FRONTEND_DASHBOARD_URL",
                "http://localhost:8000",
            ),
        }

        # Email agent
        send_mail(
            subject=f"New Lead: {lead.property_link.title}",
            message=render_to_string(
                "pages/notifications/lead_notification.txt",
                context,
            ),
            html_message=render_to_string(
                "pages/notifications/lead_notification.html",
                context,
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[lead.agent.user.email],
            fail_silently=False,
        )

        # Email user
        send_mail(
            subject=f"Your inquiry about {lead.property_link.title}",
            message=render_to_string(
                "pages/notifications/lead_confirmation.txt",
                context,
            ),
            html_message=render_to_string(
                "pages/notifications/lead_confirmation.html",
                context,
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[lead.user.email],
            fail_silently=False,
        )

        # Notification
        Notification.objects.create(
            user=lead.agent.user,
            notification_type=NotificationType.NEW_LEAD,
            title=f"New Lead from {lead.user.profile.full_name}",
            message=f"Interested in {lead.property_link.title}",
            metadata={
                "lead_id": str(lead.id),
                "property_id": str(lead.property_link.id),
            },
        )

    except Exception as e:
        logger.error(f"Failed to process new lead: {e!s}", exc_info=True)


def process_viewing_scheduled(viewing):
    try:
        lead = viewing.lead
        user = lead.user
        agent = lead.agent.user

        if not hasattr(agent, "agent_profile"):
            raise ValueError("Associated agent has no profile")

        if not hasattr(user, "profile"):
            raise ValueError("User has no profile")

        context = {
            "lead": lead,
            "viewing": viewing,
            "property": lead.property_link,
            "agent": agent.agent_profile,
            "user": user.profile,
            "dashboard_url": getattr(
                settings,
                "FRONTEND_DASHBOARD_URL",
                "http://localhost:8000",
            ),
        }

        # Email user
        send_mail(
            subject=f"Viewing Scheduled: {lead.property_link.title}",
            message=render_to_string(
                "pages/notifications/viewing_schedule_user.txt",
                context,
            ),
            html_message=render_to_string(
                "pages/notifications/viewing_schedule_user.html",
                context,
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        # Email agent
        send_mail(
            subject=f"Viewing Scheduled for Lead: {user.profile.full_name}",
            message=render_to_string(
                "pages/notifications/viewing_schedule_agent.txt",
                context,
            ),
            html_message=render_to_string(
                "pages/notifications/viewing_schedule_agent.html",
                context,
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[agent.email],
            fail_silently=False,
        )

        # Notification to agent (optional)
        Notification.objects.create(
            user=agent,
            notification_type=NotificationType.VIEWING,
            title=f"Viewing Scheduled for {user.profile.name}",
            message=f"{user.profile.name} has a scheduled viewing for {lead.property_link.title}.",
            metadata={
                "viewing_id": str(viewing.id),
                "lead_id": str(lead.id),
                "property_id": str(lead.property_link.id),
            },
        )

    except Exception as e:
        logger.error(
            f"Failed to process viewing scheduled notification: {e!s}",
            exc_info=True,
        )
