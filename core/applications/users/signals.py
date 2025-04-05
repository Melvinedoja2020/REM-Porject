from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_migrate
from django.dispatch import receiver

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
