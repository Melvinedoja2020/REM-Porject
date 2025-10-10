# subscriptions/urls.py
from django.urls import path
from .views import (
    StartSubscriptionView,
    SubscriptionDetailView,
    VerifySubscriptionView,
    InitiatePaymentView,
)
from .webhook import paystack_webhook

app_name = "subscriptions"

urlpatterns = [
    path("start/", StartSubscriptionView.as_view(), name="start"),
    path("verify/", VerifySubscriptionView.as_view(), name="verify"),
    path(
        "webhook/paystack/", paystack_webhook, name="webhook_paystack"
    ),  # configure this in Paystack dashboard
    path(
        "subscription/initiate/<str:plan_id>/",
        InitiatePaymentView.as_view(),
        name="initiate_payment",
    ),
    path("<str:pk>/", SubscriptionDetailView.as_view(), name="detail"),
]
