# subscriptions/webhooks.py
import json, hmac, hashlib, logging
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpResponseForbidden
from django.conf import settings
from core.helper.utils import handle_paystack_payment

logger = logging.getLogger(__name__)

@csrf_exempt
def paystack_webhook(request):
    if request.method != "POST":
        return HttpResponseForbidden("Invalid method")

    signature = request.headers.get("x-paystack-signature")
    if not signature:
        logger.warning("Missing x-paystack-signature")
        return HttpResponseForbidden("Missing signature")

    payload = request.body
    computed = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode(), payload, hashlib.sha512
    ).hexdigest()

    if not hmac.compare_digest(computed, signature):
        logger.warning("Invalid Paystack signature")
        return HttpResponseForbidden("Invalid signature")

    try:
        event = json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError:
        logger.exception("Invalid JSON payload")
        return HttpResponseForbidden("Invalid payload")

    event_name = event.get("event")
    data = event.get("data", {})
    reference = data.get("reference")
    status = data.get("status")

    if event_name == "charge.success" and status == "success" and reference:
        try:
            handle_paystack_payment(reference, data.get("amount", 0), status)
        except Exception as e:
            logger.exception("Webhook processing failed for %s", reference)
            return HttpResponse(status=500)

    return HttpResponse(status=200)
