# core/applications/subscriptions/api/views.py

from __future__ import annotations

from core.applications.subscriptions.api.serializers import (
    CurrentSubscriptionSerializer,
)
from core.applications.subscriptions.api.serializers import (
    SubscriptionUpgradeSerializer,
)
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.applications.property.permissions import IsVerifiedAgent
from core.applications.subscriptions.services.boost import upgrade_subscription


class SubscriptionViewSet(ViewSet):
    """
    Subscription management endpoints for agents.

    All endpoints require a verified agent account.
    Business logic fully delegated to services/boost.py.
    """
    permission_classes = [IsVerifiedAgent]

    @action(detail=False, methods=["get"], url_path="my-plan")
    def my_plan(self, request: Request) -> Response:
        """
        Returns the agent's current subscription with usage stats.
        GET /api/v1/subscriptions/my-plan/
        """
        from core.applications.subscriptions.models import AgentSubscription

        subscription = (
            AgentSubscription.objects
            .select_related("agent", "agent__user")
            .prefetch_related(
                "agent__properties",
                "agent__featured_properties",
            )
            .filter(
                agent=request.user.agent_profile,
                is_active=True,
            )
            .first()
        )

        if not subscription:
            return Response(
                {"detail": "No active subscription found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CurrentSubscriptionSerializer(subscription)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="upgrade")
    def upgrade(self, request: Request) -> Response:
        """
        Upgrade or downgrade subscription plan after Paystack payment.
        POST /api/v1/subscriptions/upgrade/

        - Requires valid Paystack transaction_id and amount
        - Excess boosts trimmed automatically on downgrade
        - New plan takes effect immediately
        """
        serializer = SubscriptionUpgradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_subscription = upgrade_subscription(
            agent=request.user.agent_profile,
            new_plan=serializer.validated_data["new_plan"],
            transaction_id=serializer.validated_data["transaction_id"],
            amount=serializer.validated_data["amount"],
        )

        output = CurrentSubscriptionSerializer(new_subscription)
        return Response(output.data, status=status.HTTP_200_OK)
