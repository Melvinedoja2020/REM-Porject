# payments/paystack_api.py
import requests
import logging
from decimal import Decimal
from django.conf import settings

logger = logging.getLogger(__name__)

PAYSTACK_BASE = getattr(settings, "PAYSTACK_BASE_URL", "https://api.paystack.co")
SECRET_KEY = getattr(settings, "PAYSTACK_SECRET_KEY")
TIMEOUT = getattr(settings, "PAYSTACK_TIMEOUT", 15)


class PaystackAPI:
    """
    Service wrapper for Paystack API.
    Provides transaction initialization and verification with
    consistent error handling.
    """

    @staticmethod
    def _headers() -> dict:
        return {
            "Authorization": f"Bearer {SECRET_KEY}",
            "Content-Type": "application/json",
        }

    # === Transaction Init === #
    @staticmethod
    def initialize_transaction(
        email: str, amount: Decimal, callback_url: str, metadata: dict | None = None
    ) -> dict:
        """
        Initialize a Paystack transaction and return response.
        Always returns dict: {success: bool, message: str, data: dict|None}
        """
        logger.info(
            "[PaystackAPI] Initializing transaction for email=%s amount=%s",
            email,
            amount,
        )
        try:
            payload = {
                "email": email,
                "amount": int(amount * 100),  # convert Naira → Kobo
                "callback_url": callback_url,
                "metadata": metadata or {},
            }
            resp = requests.post(
                f"{PAYSTACK_BASE}/transaction/initialize",
                json=payload,
                headers=PaystackAPI._headers(),
                timeout=TIMEOUT,
            )
            data = resp.json()
            if resp.status_code != 200 or not data.get("status"):
                logger.warning("Paystack init failed: %s", data)
                return {
                    "success": False,
                    "message": data.get("message", "Init failed"),
                    "data": None,
                }

            return {
                "success": True,
                "message": "Transaction initialized",
                "data": data.get("data"),
            }

        except requests.RequestException as e:
            logger.error("Paystack init error: %s", str(e), exc_info=True)
            return {
                "success": False,
                "message": "Network error contacting Paystack",
                "data": None,
            }
        except Exception:
            logger.exception("Unexpected Paystack init error")
            return {
                "success": False,
                "message": "Unexpected error occurred",
                "data": None,
            }

    # === Transaction Verify === #
    @staticmethod
    def verify_transaction(reference: str) -> dict:
        """
        Verify a Paystack transaction.
        Always returns dict: {success: bool, message: str, data: dict|None}
        """
        try:
            resp = requests.get(
                f"{PAYSTACK_BASE}/transaction/verify/{reference}",
                headers=PaystackAPI._headers(),
                timeout=TIMEOUT,
            )
            data = resp.json()
            if resp.status_code != 200 or not data.get("status"):
                logger.warning("Paystack verify failed: %s", data)
                return {
                    "success": False,
                    "message": data.get("message", "Verification failed"),
                    "data": None,
                }

            return {
                "success": True,
                "message": "Transaction verified",
                "data": data.get("data"),
            }

        except requests.RequestException as e:
            logger.error("Paystack verify error: %s", str(e), exc_info=True)
            return {
                "success": False,
                "message": "Network error contacting Paystack",
                "data": None,
            }
        except Exception:
            logger.exception("Unexpected Paystack verify error")
            return {
                "success": False,
                "message": "Unexpected error occurred",
                "data": None,
            }
