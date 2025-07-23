import auto_prefetch
from django.db import models

from core.helper.models import UIDTimeBasedModel


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
        "users.User",
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
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("paid", "Paid"),
            ("failed", "Failed"),
        ],
        default="pending",
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
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
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


class PremiumServiceSubscription(UIDTimeBasedModel):
    """
    Tracks the premium service subscriptions of agents for enhanced visibility and additional features.
    """

    agent = auto_prefetch.ForeignKey(
        "users.AgentProfile",
        on_delete=models.CASCADE,
        related_name="premium_subscriptions",
    )
    service_type = models.CharField(
        max_length=50,
        choices=[
            ("standard", "Standard"),
            ("premium", "Premium"),
            ("enterprise", "Enterprise"),
        ],
        default="standard",
    )
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("active", "Active"),
            ("expired", "Expired"),
            ("pending", "Pending"),
        ],
        default="pending",
    )
    amount_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    transaction_id = models.CharField(max_length=255, null=True, blank=True)

    class Meta(auto_prefetch.Model.Meta):
        ordering = ["-start_date"]
        verbose_name = "Premium Service Subscription"
        verbose_name_plural = "Premium Service Subscriptions"

    def __str__(self):
        return f"{self.agent.user.get_full_name()} - {self.service_type} Subscription ({self.status})"

    def is_active(self):
        """
        Returns whether the subscription is currently active based on the current date and the end date.
        """
        return self.status == "active" and (
            self.end_date is None or self.end_date >= timezone.now()
        )
