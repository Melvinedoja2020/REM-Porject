from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

from core.applications.notifications.models import Notification
from core.applications.property.models import Lead, PropertyViewing
from core.helper.enums import NotificationType



@receiver(post_save, sender=PropertyViewing)
def handle_viewing_status_change(sender, instance, created, **kwargs):
    
    if not created and instance.lead:
        # Update lead status when viewing is completed
        if instance.status == PropertyViewing.StatusChoices.COMPLETED:
            instance.lead.status = Lead.StatusChoices.FOLLOW_UP
            instance.lead.save()
            
        # Notify agent and client about status changes
        if 'status' in kwargs.get('update_fields', []):
            send_mail(
                subject=f"Viewing Update: {instance.property_link.title}",
                message=f"Viewing status changed to {instance.get_status_display()}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[
                    instance.lead.agent.user.email,
                    instance.user.email
                ]
            )

@receiver(post_save, sender=Lead)
def handle_new_lead(sender, instance, created, **kwargs):
    logger.debug(f"Signal triggered for lead ID <<<<<>>>>{instance.id}, created={created}")
    if created:
        try:
            # Ensure we have valid agent and user profiles
            if not hasattr(instance.agent.user, 'agent_profile'):
                raise ValueError("Associated agent has no profile")
            
            if not hasattr(instance.user, 'profile'):
                raise ValueError("Lead user has no profile")

            # Prepare context for templates
            context = {
                'lead': instance,
                'agent': instance.agent.user.agent_profile,
                'user': instance.user.profile,
                'property': instance.property_link,
                'dashboard_url': settings.FRONTEND_DASHBOARD_URL
            }

            # 1. Send email to agent
            send_mail(
                subject=f"New Lead: {instance.property_link.title}",
                message=render_to_string('pages/notifications/lead_notification.txt', context),
                html_message=render_to_string('pages/notifications/lead_notification.html', context),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[instance.agent.user.email],
                fail_silently=False
            )

            # 2. Send confirmation to user
            send_mail(
                subject=f"Your inquiry about {instance.property_link.title}",
                message=render_to_string('pages/notifications/lead_confirmation.txt', context),
                html_message=render_to_string('pages/notifications/lead_confirmation.html', context),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[instance.user.email],
                fail_silently=False
            )

            # 3. Create notification in database
            Notification.objects.create(
                user=instance.agent.user,
                notification_type=NotificationType.NEW_LEAD,
                title=f"New Lead from {instance.user.profile.full_name}",
                message=f"Interested in {instance.property_link.title}",
                metadata={
                    'lead_id': str(instance.id),
                    'property_id': str(instance.property_link.id)
                }
            )

        except Exception as e:
            # Log the error but don't crash the application
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to process lead signal: {str(e)}", exc_info=True)


