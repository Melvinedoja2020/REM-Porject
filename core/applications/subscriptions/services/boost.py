from __future__ import annotations

from django.db import transaction as db_transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound

from core.applications.property.models import Property
from core.applications.subscriptions.models import FeaturedListing


def boost_property(*, agent, property_id: str, transaction_id: str, amount: float):
    """
    Creates a FeaturedListing after successful Paystack payment.
    Enforces plan-based featured listing limits via model.save().
    """

    try:
        prop = Property.objects.get(pk=property_id, agent=agent)
    except Property.DoesNotExist:
        msg = "Property not found or does not belong to this agent."
        raise NotFound(msg)

    with db_transaction.atomic():
        featured = FeaturedListing(
            property=prop,
            agent=agent,
            transaction_id=transaction_id,
            amount_paid=amount,
        )
        featured.full_clean()
        featured.save()

        Property.objects.filter(pk=prop.pk).update(is_featured=True)

    return featured


def deactivate_expired_boosts() -> int:
    """
    Called by a periodic task (Celery beat) to expire stale boosts.
    Returns count of deactivated listings.
    """

    expired = FeaturedListing.objects.filter(
        is_active=True,
        end_date__lt=timezone.now(),
    )
    count = expired.count()

    # Capture IDs before update — queryset won't match after is_active flips
    expired_property_ids = list(expired.values_list("property_id", flat=True))
    expired.update(is_active=False)

    Property.objects.filter(pk__in=expired_property_ids).update(is_featured=False)

    return count
