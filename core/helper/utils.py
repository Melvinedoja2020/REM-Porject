import uuid
import secrets
from decimal import Decimal
from django.db import transaction

import logging

from typing import Optional
from django.db import models
from django.db.models import Exists, OuterRef
from django.utils import timezone



logger = logging.getLogger(__name__)


def generate_payment_reference(prefix="sub"):
    """
    Generate a unique payment reference.
    Example: sub_202509301548_ab12cd34ef
    """
    random_token = secrets.token_hex(5)  # shorter than uuid, still unique enough
    return f"{prefix}_{uuid.uuid4().hex[:8]}_{random_token}"


def handle_paystack_payment(
    reference: str,
    amount_kobo: int,
    status: str,
    user=None,
    plan_key: Optional[str] = None,
):
    """
    Handle Paystack payment in an idempotent way.
    Can be called from both webhook and VerifySubscriptionView.

    Args:
        reference: Paystack transaction reference
        amount_kobo: Amount in Kobo (int)
        status: Transaction status (e.g., "success", "failed")
        user: Django User instance (optional, required for manual verification)
        plan_key: Subscription plan key (optional)

    Returns:
        Payment object
    """
    # Lazy import to avoid circular dependency
    from core.applications.subscriptions.models import (
        Payment,
        AgentSubscription,
        PlanConfig,
    )

    amount = Decimal(amount_kobo) / 100

    with transaction.atomic():
        payment, created = Payment.objects.get_or_create(
            reference=reference,
            defaults={
                "amount": amount,
                "status": status,
                "user": user,
            },
        )

        if not created:
            # Already exists → only update if still pending
            if payment.status == "success":
                logger.info("Payment %s already processed. Skipping.", reference)
                return payment

            payment.status = status
            payment.amount = amount
            payment.save(update_fields=["status", "amount"])
            logger.info(
                "Updated existing payment %s with new status %s", reference, status
            )

        # --- Handle subscription linking ---
        if plan_key:
            plan_config = PlanConfig.objects.filter(plan=plan_key).first()
            if not plan_config:
                raise ValueError(f"Invalid subscription plan: {plan_key}")

            if payment.amount < plan_config.price:
                raise ValueError(
                    f"Payment {payment.amount} does not match plan {plan_config.plan} price {plan_config.price}"
                )

            if not payment.subscription:
                if not user:
                    raise ValueError("User is required to attach subscription")

                agent = user.agent_profile
                sub = AgentSubscription.objects.create(
                    agent=agent,
                    plan=plan_config.plan,
                    transaction_id=reference,
                    amount_paid=payment.amount,
                )
                payment.subscription = sub
                payment.save(update_fields=["subscription"])
                logger.info(
                    "Created new subscription %s for payment %s", sub.pk, reference
                )
            else:
                sub = payment.subscription
                logger.info(
                    "Using existing subscription %s for payment %s", sub.pk, reference
                )

            # Renew subscription
            sub.renew(transaction_id=reference, amount=payment.amount)
            sub.agent.set_current_subscription(sub)
            logger.info("Subscription %s renewed for agent %s", sub.pk, sub.agent_id)

        logger.info("Processed Paystack payment %s successfully", reference)

    return payment


from django.db import models
from django.db.models import Exists, OuterRef
from django.utils import timezone


class PropertyQuerySet(models.QuerySet):
    """Custom queryset for Property with helpers for featured listings."""

    def with_featured_flag(self):
        """Annotate each property with a boolean flag indicating if it's featured."""
        from core.applications.subscriptions.models import FeaturedListing
        now = timezone.now()
        return self.annotate(
            is_featured_flag=Exists(
                FeaturedListing.objects.filter(
                    property=OuterRef("pk"),
                    is_active=True,
                    end_date__gte=now,
                )
            )
        )

    def featured_first(self):
        """Order properties so featured ones appear first."""
        return self.with_featured_flag().order_by("-is_featured_flag", "-created_at")

    def available(self):
        """Filter for available properties."""
        return self.filter(is_available=True)
