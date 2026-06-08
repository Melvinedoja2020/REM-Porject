from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name="subscriptions.deactivate_expired_boosts",
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # retry after 60 seconds on failure
)
def deactivate_expired_boosts_task(self) -> str:
    """
    Periodic task that deactivates expired FeaturedListing records
    and syncs the ``is_featured`` flag on affected Property rows.

    Scheduled every 6 hours via Celery beat.

    Retries up to 3 times with a 60-second delay on unexpected failure.

    Returns:
        A summary string logged by the Celery worker.
    """
    try:
        from core.applications.subscriptions.services.boost import deactivate_expired_boosts

        count = deactivate_expired_boosts()
        msg = f"Successfully deactivated {count} expired featured listing(s)."
        logger.info(msg)
        return msg

    except Exception as exc:
        logger.exception(
            "deactivate_expired_boosts_task failed — attempt %s/%s: %s",
            self.request.retries + 1,
            self.max_retries + 1,
            exc,
        )
        raise self.retry(exc=exc)


@shared_task(
    name="subscriptions.deactivate_expired_subscriptions",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def deactivate_expired_subscriptions_task(self) -> str:
    """
    Periodic task that deactivates expired AgentSubscription records.
    Runs daily via Celery beat.

    An expired subscription is one where:
      - ``is_active=True``
      - ``end_date`` is not None (FREE tier never expires)
      - ``end_date`` is in the past

    Returns:
        A summary string logged by the Celery worker.
    """
    try:
        from core.applications.subscriptions.services.boost import deactivate_expired_subscriptions

        count = deactivate_expired_subscriptions()
        msg = f"Successfully deactivated {count} expired subscription(s)."
        logger.info(msg)
        return msg

    except Exception as exc:
        logger.exception(
            "deactivate_expired_subscriptions_task failed — attempt %s/%s: %s",
            self.request.retries + 1,
            self.max_retries + 1,
            exc,
        )
        raise self.retry(exc=exc)
