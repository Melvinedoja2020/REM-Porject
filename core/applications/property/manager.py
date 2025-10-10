from django.db import models

from core.helper.utils import PropertyQuerySet


class PropertyManager(models.Manager.from_queryset(PropertyQuerySet)):
    """Manager for Property model with custom queryset methods."""

    def get_queryset(self):
        """Use featured-first ordering by default."""
        return super().get_queryset().featured_first()
