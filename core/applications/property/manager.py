from django.db import models

from core.applications.property.querysets.property_queryset import (
    AmenityQuerySet,
    FavoritePropertyQuerySet,
)
from core.applications.property.querysets.property_queryset import LeadQuerySet
from core.applications.property.querysets.property_queryset import PropertyQuerySet
from core.applications.property.querysets.property_queryset import (
    PropertySubscriptionQuerySet,
)
from core.applications.property.querysets.property_queryset import (
    PropertyViewingQuerySet,
)

PropertyManager = models.Manager.from_queryset(PropertyQuerySet)
LeadManager = models.Manager.from_queryset(LeadQuerySet)
PropertyViewingManager = models.Manager.from_queryset(PropertyViewingQuerySet)
FavoritePropertyManager = models.Manager.from_queryset(FavoritePropertyQuerySet)
PropertySubscriptionManager = models.Manager.from_queryset(PropertySubscriptionQuerySet)
AmenityManager = models.Manager.from_queryset(AmenityQuerySet)
