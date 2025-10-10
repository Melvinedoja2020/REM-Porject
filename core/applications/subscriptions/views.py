# views.py
import logging
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import DetailView
from django.views import View
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin

from core.applications.subscriptions.models import (
    AgentSubscription,
    Payment,
    PlanConfig,
)
from core.applications.subscriptions.services.paystack import PaystackAPI


logger = logging.getLogger(__name__)


class StartSubscriptionView(LoginRequiredMixin, View):
    """Display subscription plans and redirect active users to dashboard."""

    def get(self, request):
        logger.info("StartSubscriptionView: user=%s", request.user.email)
        plans = PlanConfig.objects.all().order_by("price")
        agent = request.user.agent_profile

        # Redirect if agent already has an active subscription
        if agent.current_subscription and agent.current_subscription.is_active:
            logger.info(
                "User %s already has active subscription %s. Redirecting to dashboard.",
                request.user.email,
                agent.current_subscription.id,
            )
            messages.info(request, "✅ You already have an active subscription.")
            return redirect("users:agent_dashboard")

        logger.info("Rendering subscription plans for user %s", request.user.email)
        return render(
            request, "subscriptions/start_subscription.html", {"plans": plans}
        )


class InitiatePaymentView(LoginRequiredMixin, View):
    """Handles subscription payment initiation via Paystack."""

    def post(self, request, plan_id):
        logger.info(
            "Initiating payment for user=%s plan_id=%s", request.user.email, plan_id
        )
        agent = request.user.agent_profile
        plan = get_object_or_404(PlanConfig, id=plan_id)

        logger.debug("Fetched plan: %s (price=%s)", plan.plan, plan.price)

        # --- Handle free trial
        if (
            plan.plan == "Basic"
            and not agent.subscriptions.filter(is_trial=True).exists()
        ):
            logger.info(
                "Granting free trial for user=%s plan=%s", request.user.email, plan.plan
            )
            trial = AgentSubscription.objects.create(
                agent=agent,
                plan=plan.plan,
                is_trial=True,
                is_active=True,
                amount_paid=Decimal("0.00"),
            )
            agent.set_current_subscription(trial)
            messages.success(request, "🎉 Your free 1-month trial has started!")
            return redirect("users:agent_dashboard")

        # --- Initialize Paystack transaction
        callback_url = request.build_absolute_uri(reverse("subscriptions:verify"))
        logger.debug("Callback URL built: %s", callback_url)

        resp = PaystackAPI.initialize_transaction(
            email=request.user.email,
            amount=plan.price,
            callback_url=callback_url,
            metadata={"agent_id": str(agent.id), "plan": plan.plan},
        )
        logger.info("Paystack init response: %s", resp)

        if not resp.get("success"):
            logger.error(
                "Payment initialization failed for user=%s: %s",
                request.user.email,
                resp,
            )
            messages.error(request, f"Payment initialization failed: {resp['message']}")
            return redirect("subscriptions:start")

        data = resp["data"]
        reference = data.get("reference")
        auth_url = data.get("authorization_url")

        if not reference or not auth_url:
            logger.error(
                "Paystack returned no reference/auth_url for user=%s",
                request.user.email,
            )
            messages.error(request, "❌ Could not get Paystack payment link.")
            return redirect("subscriptions:start")

        # --- Create/Update subscription
        subscription, created = AgentSubscription.objects.update_or_create(
            agent=agent,
            transaction_id=reference,
            defaults={
                "plan": plan.plan,
                "amount_paid": plan.price,
                "is_active": False,
            },
        )
        logger.info(
            "Subscription %s for user=%s created=%s reference=%s amount=%s",
            subscription.id,
            request.user.email,
            created,
            reference,
            plan.price,
        )

        # --- Create/Update Payment
        payment, created = Payment.objects.update_or_create(
            reference=reference,
            defaults={
                "user": request.user,
                "subscription": subscription,
                "amount": plan.price,
                "status": "pending",
                "payment_method": "paystack",
            },
        )
        logger.info(
            "Payment %s for user=%s created=%s reference=%s amount=%s status=pending",
            payment.id,
            request.user.email,
            created,
            reference,
            plan.price,
        )

        logger.info(
            "Redirecting user=%s to Paystack checkout: %s", request.user.email, auth_url
        )
        return redirect(auth_url)


class VerifySubscriptionView(LoginRequiredMixin, View):
    """Verify Paystack payment and activate/renew subscription."""

    def get(self, request):
        reference = request.GET.get("reference")
        logger.info(
            "Verifying payment for user=%s reference=%s", request.user.email, reference
        )

        if not reference:
            logger.error(
                "Verification failed: missing reference for user=%s", request.user.email
            )
            messages.error(request, "❌ Missing transaction reference.")
            return redirect("subscriptions:start")

        try:
            payment = Payment.objects.get(reference=reference, user=request.user)
            logger.debug("Fetched Payment %s for reference=%s", payment.id, reference)
        except Payment.DoesNotExist:
            logger.error(
                "Payment not found for user=%s reference=%s",
                request.user.email,
                reference,
            )
            messages.error(request, "❌ Invalid or unknown payment reference.")
            return redirect("subscriptions:start")

        resp = PaystackAPI.verify_transaction(reference)
        logger.info("Paystack verify response: %s", resp)

        if not resp.get("success"):
            logger.error(
                "Verification failed for user=%s: %s", request.user.email, resp
            )
            messages.error(request, f"❌ Verification failed: {resp['message']}")
            return redirect("subscriptions:start")

        data = resp["data"]
        amount_paid = Decimal(data["amount"]) / 100
        plan_key = data["metadata"].get("plan")

        logger.debug(
            "Verification success: user=%s reference=%s plan=%s amount=%s",
            request.user.email,
            reference,
            plan_key,
            amount_paid,
        )

        # --- Update payment
        payment.amount = amount_paid
        payment.status = "success"
        payment.save(update_fields=["amount", "status"])
        logger.info(
            "Payment %s updated: status=success amount=%s", payment.id, amount_paid
        )

        # --- Ensure subscription exists
        subscription = payment.subscription
        if not subscription:
            logger.warning(
                "No subscription found for payment %s. Creating new.", payment.id
            )
            subscription = AgentSubscription.objects.create(
                agent=request.user.agent_profile,
                plan=plan_key,
                transaction_id=reference,
                amount_paid=amount_paid,
            )
            payment.subscription = subscription
            payment.save(update_fields=["subscription"])

        # --- Renew/activate subscription
        subscription.renew(transaction_id=reference, amount=amount_paid)
        subscription.agent.set_current_subscription(subscription)
        logger.info(
            "Subscription %s activated for user=%s", subscription.id, request.user.email
        )

        messages.success(
            request, f"✅ {subscription.get_plan_display()} subscription activated."
        )
        return redirect("subscriptions:detail", pk=subscription.pk)


class SubscriptionDetailView(LoginRequiredMixin, DetailView):
    """
    Displays detailed information about a user's subscription.
    """
    model = AgentSubscription
    template_name = "subscriptions/subscription_detail.html"
    context_object_name = "subscription"
    pk_url_kwarg = "pk"

    def get_queryset(self):
        """
        Ensure that users can only view their own subscriptions.
        """
        return AgentSubscription.objects.filter(agent=self.request.user.agent_profile)
