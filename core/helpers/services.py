# subscriptions/services.py
from django.core.exceptions import ValidationError

from core.applications.subscriptions.features import FEATURE_LIMITS
from core.helpers.enums import SubscriptionPlan


class SubscriptionService:
    """Service class for subscription-related operations."""

    @staticmethod
    def get_agent_plan(agent):
        """Return agent's current plan, defaults to FREE."""
        subscription = getattr(agent, "current_subscription", None)
        if subscription and subscription.is_valid():
            return subscription.plan
        return SubscriptionPlan.FREE

    @staticmethod
    def check_feature_limit(agent, feature_name: str, current_count: int):
        """
        Ensure agent has not exceeded the feature limit for their plan.
        """
        plan = SubscriptionService.get_agent_plan(agent)
        limit = FEATURE_LIMITS.get(plan, {}).get(feature_name)

        if limit is not None and current_count >= limit:
            raise ValidationError(
                f"You have reached the {feature_name.replace('_', ' ')} "
                f"limit ({limit}) for the {plan} plan. Please upgrade."
            )


# ---------------------------------------------------------------------------
# Sendexa service stub
# ---------------------------------------------------------------------------


class SendexaService:
    """
    Sendexa SMS OTP integration.

    Replace the stubs below with real Sendexa API calls once you have
    your API key.  Docs: https://docs.sendexa.co

    Expected env vars (add to your .env / settings):
        SENDEXA_API_KEY  = "sx_live_xxxxxxxxxxxx"
        SENDEXA_SENDER_ID = "REM"          # your approved sender ID
    """

    @staticmethod
    def send_otp(phone_number: str) -> bool:
        """
        Send a one-time password to *phone_number* via Sendexa SMS.

        TODO: replace stub with real implementation:

            import requests
            from django.conf import settings

            response = requests.post(
                "https://api.sendexa.co/v1/otp/send",
                headers={"Authorization": f"Bearer {settings.SENDEXA_API_KEY}"},
                json={
                    "phone": phone_number,
                    "sender_id": settings.SENDEXA_SENDER_ID,
                    "length": 6,
                    "expiry": 10,          # minutes
                },
                timeout=10,
            )
            return response.status_code == 200
        """
        # STUB — always returns True in development
        import logging
        logging.getLogger(__name__).info(
            "[SendexaService.send_otp] STUB — OTP would be sent to %s", phone_number
        )
        return True

    @staticmethod
    def verify_otp(phone_number: str, otp: str) -> bool:
        """
        Verify *otp* for *phone_number* with Sendexa.

        TODO: replace stub with real implementation:

            import requests
            from django.conf import settings

            response = requests.post(
                "https://api.sendexa.co/v1/otp/verify",
                headers={"Authorization": f"Bearer {settings.SENDEXA_API_KEY}"},
                json={"phone": phone_number, "otp": otp},
                timeout=10,
            )
            return response.status_code == 200
        """
        # STUB — accepts any 6-digit OTP in development
        import logging
        logging.getLogger(__name__).info(
            "[SendexaService.verify_otp] STUB — verifying OTP %s for %s",
            otp,
            phone_number,
        )
        return len(otp) == 6
