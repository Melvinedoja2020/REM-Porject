import auto_prefetch
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta

from core.applications.subscriptions.features import FEATURE_LIMITS
from core.applications.subscriptions.services.paystack import PaystackAPI
from core.helper.enums import PaymentStatus, SubscriptionPlan
from core.helper.models import UIDTimeBasedModel
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.urls import reverse

from core.helper.utils import generate_payment_reference


# -------------------------------
# RENTAL TRANSACTION & COMMISSION
# -------------------------------
class RentalTransaction(UIDTimeBasedModel):
    """
    Represents a rental transaction between an agent and a buyer.
    """

    property = auto_prefetch.ForeignKey(
        "property.Property",
        on_delete=models.CASCADE,
        related_name="rental_transactions",
    )
    agent = auto_prefetch.ForeignKey(
        "users.AgentProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agent_rentals",
    )
    buyer = auto_prefetch.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="buyer_rentals",
    )
    referred_by = auto_prefetch.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referral_rentals",
    )

    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_status = models.CharField(
        max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING
    )
    completed = models.BooleanField(default=False)
    date = models.DateTimeField(auto_now_add=True)

    class Meta(auto_prefetch.Model.Meta):
        ordering = ["-date"]
        verbose_name = "Rental Transaction"
        verbose_name_plural = "Rental Transactions"

    def __str__(self):
        return f"{self.property} - ₦{self.total_amount:,} ({self.payment_status})"


class AgentCommission(UIDTimeBasedModel):
    """
    Tracks commission owed or paid to an agent for a rental transaction.
    """

    agent = auto_prefetch.ForeignKey(
        "users.AgentProfile",
        on_delete=models.CASCADE,
        related_name="commissions",
    )
    rental = auto_prefetch.ForeignKey(
        "subscriptions.RentalTransaction",
        on_delete=models.CASCADE,
        related_name="commissions",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Commission percentage",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("paid", "Paid"),
        ],
        default="pending",
    )
    paid_on = models.DateTimeField(null=True, blank=True)

    class Meta(auto_prefetch.Model.Meta):
        ordering = ["-created_at"]
        verbose_name = "Agent Commission"
        verbose_name_plural = "Agent Commissions"

    def __str__(self):
        return f"{self.agent.user.get_full_name()} - ₦{self.amount or 0:.2f} ({self.status})"

    def calculate_commission(self, save=True):
        """
        Calculates and optionally saves the agent commission based on percentage.
        """
        if self.rental and self.percentage:
            self.amount = (self.rental.total_amount * self.percentage) / 100
            if save:
                self.save()

    @property
    def is_paid(self):
        return self.status == "paid"


# -------------------------------
# SUBSCRIPTION PLAN & FEATURED ADS
# -------------------------------


class AgentSubscription(UIDTimeBasedModel):
    """
    Tracks agent annual subscription plans (Basic, Premium, Enterprise).
    """

    agent = auto_prefetch.ForeignKey(
        "users.AgentProfile",
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    plan = models.CharField(
        max_length=20, choices=SubscriptionPlan.choices, default=SubscriptionPlan.BASIC
    )
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_trial = models.BooleanField(default=False)
    amount_paid = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    transaction_id = models.CharField(max_length=255, null=True, blank=True)
    auto_renew = models.BooleanField(default=False)

    class Meta(auto_prefetch.Model.Meta):
        ordering = ["-start_date"]
        verbose_name = "Agent Subscription"
        verbose_name_plural = "Agent Subscriptions"

    def __str__(self):
        return f"{self.agent.user.name} - {self.plan} ({'Active' if self.is_active else 'Expired'})"

    def save(self, *args, **kwargs):
        """
        Automatically set duration:
        - Trial: 30 days (or configurable later)
        - Paid: use PlanConfig.duration_days
        """
        if not self.end_date:
            if self.is_trial:
                self.end_date = self.start_date + timedelta(days=30)
            else:
                try:
                    plan_cfg = PlanConfig.get_plan(self.plan)
                    self.end_date = self.start_date + timedelta(
                        days=plan_cfg.duration_days
                    )
                except PlanConfig.DoesNotExist:
                    # fallback safety
                    self.end_date = self.start_date + timedelta(days=365)
        super().save(*args, **kwargs)

    def is_valid(self):
        """Check if subscription is still valid."""
        return self.is_active and timezone.now() <= self.end_date

    @property
    def is_expired(self):
        """Check if subscription has expired."""
        return self.end_date and timezone.now() > self.end_date

    def activate_trial(self):
        """
        Activate a 30-day trial subscription for the agent.
        Ensures only one trial per agent.
        """
        if self.agent.subscriptions.filter(is_trial=True).exists():
            raise ValidationError("Agent already used trial.")

        self.is_trial = True
        self.is_active = True
        self.start_date = timezone.now()
        self.end_date = self.start_date + timedelta(days=30)
        self.amount_paid = Decimal("0.00")
        self.transaction_id = None
        self.save()

    def remaining_days(self) -> int | None:
        """Days left before subscription expires."""
        if not self.end_date:
            return None
        return max((self.end_date - timezone.now()).days, 0)

    def renew(self, transaction_id: str, amount: float):
        """Renew subscription after successful Paystack payment."""
        if not transaction_id:
            raise ValidationError("Transaction ID is required for renewal.")

        try:
            plan_cfg = PlanConfig.get_plan(self.plan)
            duration = plan_cfg.duration_days
        except PlanConfig.DoesNotExist:
            duration = 365  # fallback

        self.start_date = timezone.now()
        self.end_date = self.start_date + timedelta(days=duration)
        self.is_trial = False
        self.amount_paid = amount
        self.transaction_id = transaction_id
        self.is_active = True
        self.save()

    def upgrade_plan(self, new_plan: str, transaction_id: str, amount: float):
        """
        Upgrade/Downgrade to another plan after Paystack payment.
        Resets subscription cycle.
        """
        if new_plan not in SubscriptionPlan.values:
            raise ValidationError("Invalid subscription plan.")

        self.plan = new_plan
        self.is_trial = False
        self.transaction_id = transaction_id
        self.amount_paid = amount
        self.start_date = timezone.now()

        try:
            plan_cfg = PlanConfig.get_plan(new_plan)
            self.end_date = self.start_date + timedelta(days=plan_cfg.duration_days)
        except PlanConfig.DoesNotExist:
            self.end_date = self.start_date + timedelta(days=365)

        self.is_active = True
        self.save()

    @property
    def plan_price(self):
        try:
            return PlanConfig.get_plan(self.plan).price
        except PlanConfig.DoesNotExist:
            return Decimal("0.00")


class FeaturedListing(UIDTimeBasedModel):
    """
    Agents can pay to boost their property visibility.
    """

    property = auto_prefetch.ForeignKey(
        "property.Property",
        on_delete=models.CASCADE,
        related_name="featured_listings",
    )
    agent = auto_prefetch.ForeignKey(
        "users.AgentProfile",
        on_delete=models.CASCADE,
        related_name="featured_properties",
    )
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    amount_paid = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    transaction_id = models.CharField(max_length=255, null=True, blank=True)
    boost_duration = models.PositiveIntegerField(
        default=7, help_text="Boost duration in days"
    )

    is_active = models.BooleanField(default=True)

    class Meta(auto_prefetch.Model.Meta):
        ordering = ["-start_date"]
        verbose_name = "Featured Listing"
        verbose_name_plural = "Featured Listings"

    def __str__(self):
        return f"Boosted: {self.property} by {self.agent.user.get_full_name()}"

    def save(self, *args, **kwargs):
        """
        Enforce featured listing limits based on agent's subscription plan.
        """
        if not self.pk:  # new featured listing
            subscription = getattr(self.agent, "current_subscription", None)
            plan = subscription.plan if subscription else SubscriptionPlan.FREE

            active_boosts = self.agent.featured_properties.filter(
                is_active=True
            ).count()
            limit = FEATURE_LIMITS.get(plan, {}).get("featured_listings")

            if limit is not None and active_boosts >= limit:
                raise ValidationError(
                    f"You have reached your featured listing limit ({limit}) "
                    f"for the {plan} plan. Please upgrade your subscription."
                )

        super().save(*args, **kwargs)

    def is_currently_active(self):
        return self.is_active and (
            self.end_date is None or self.end_date >= timezone.now()
        )


class PlanConfig(UIDTimeBasedModel):
    """
    Configuration for subscription plans.
    """

    plan = models.CharField(
        max_length=20,
        choices=SubscriptionPlan.choices,
        unique=True,
    )
    price = models.DecimalField(max_digits=12, decimal_places=2)
    duration_days = models.PositiveIntegerField(default=365)
    description = models.TextField(blank=True)

    class Meta(auto_prefetch.Model.Meta):
        verbose_name = "Subscription Plan Configuration"
        verbose_name_plural = "Subscription Plans"
        ordering = ["price"]

    def __str__(self):
        return f"{self.get_plan_display()} - ₦{self.price} ({self.duration_days} days)"

    @classmethod
    def get_plan(cls, plan: str) -> "PlanConfig":
        """Fetch a plan configuration safely."""
        return cls.objects.get(plan=plan)


class Payment(models.Model):
    PAYMENT_METHODS = [
        ("paystack", "Paystack"),
        ("flutterwave", "Flutterwave"),
        ("moneypoint", "Moneypoint"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments"
    )
    subscription = models.ForeignKey(
        "subscriptions.AgentSubscription",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
        help_text="Optional link to subscription if payment is for a plan.",
    )
    reference = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Unique transaction reference.",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="NGN")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.user.email} - {self.amount} {self.currency} ({self.payment_method})"
        )

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = generate_payment_reference()
        super().save(*args, **kwargs)

    # --- Status Helpers --- #
    def mark_as_successful(self):
        self.status = "success"
        self.paid_at = timezone.now()
        self.save(update_fields=["status", "paid_at", "updated_at"])

    def mark_as_failed(self):
        self.status = "failed"
        self.save(update_fields=["status", "updated_at"])

    def mark_as_cancelled(self):
        self.status = "cancelled"
        self.save(update_fields=["status", "updated_at"])

    # --- Gateway Init --- #
    def get_checkout_url(self):
        if self.payment_method == "paystack":
            return self._init_paystack()
        elif self.payment_method == "flutterwave":
            return self._init_flutterwave()
        elif self.payment_method == "moneypoint":
            return self._init_moneypoint()
        raise ValueError("Unsupported payment method")

    def _init_paystack(self):
        callback_url = settings.SITE_URL + reverse("subscriptions:verify_payment")
        response = PaystackAPI.initialize_transaction(
            email=self.user.email,
            amount=self.amount,
            callback_url=callback_url,
            metadata={
                "payment_id": str(self.id),
                "subscription_id": str(self.subscription_id),
            },
        )
        if not response["success"]:
            raise ValueError(f"Paystack init failed: {response['message']}")
        return response["data"]["authorization_url"]

    def _init_flutterwave(self):
        raise NotImplementedError("Flutterwave integration not yet implemented")

    def _init_moneypoint(self):
        raise NotImplementedError("Moneypoint integration not yet implemented")

    # --- Verification --- #
    def verify_with_paystack(self):
        resp = PaystackAPI.verify_transaction(self.reference)
        if not resp["success"]:
            self.mark_as_failed()
            return False, resp["message"]

        data = resp["data"]
        if not data or data.get("status") != "success":
            self.mark_as_failed()
            return False, "Payment was not successful."

        # update amount & currency from Paystack
        self.amount = Decimal(data["amount"]) / 100
        self.currency = data.get("currency", "NGN")
        self.mark_as_successful()

        return True, "Payment verified successfully."
