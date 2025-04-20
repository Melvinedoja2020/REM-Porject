from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver

from core.applications.users.models import AgentProfile
from django.core.mail import send_mail
from django.conf import settings


@receiver(post_migrate)
def create_default_groups(sender, **kwargs):
    admin_group, created = Group.objects.get_or_create(name="Admin")
    agent_group, created = Group.objects.get_or_create(name="Agent")
    customer_group, created = Group.objects.get_or_create(name="Customer")

    # Assign permissions (Example: Vendor can add products)
    agent_permissions = Permission.objects.filter(codename__in=[
        "add_house", "change_house", "delete_house", "view_house",
        
    ])
    customer_group.permissions.set(agent_permissions)



@receiver(post_save, sender=AgentProfile)
def notify_agent_approval(sender, instance, created, **kwargs):
    if not created and instance.verified:
        send_mail(
            subject="Agent Profile Approved",
            message="Congratulations! Your agent profile has been verified. You can now list properties.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instance.user.email],
        )
