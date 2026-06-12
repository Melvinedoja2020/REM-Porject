from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.db.models import Avg
from django.db.models import Count
from django.utils.translation import gettext_lazy as _

from core.applications.rating.models import AgentRating
from core.applications.rating.models import RatingEligibility


class RatingService:

    @staticmethod
    def _assert_eligible(rater, agent_profile) -> "RatingEligibility":
        """
        Return the eligibility record if valid, else raise ValidationError.
        """
        try:
            eligibility = RatingEligibility.objects.get(
                rater=rater,
                agent=agent_profile,
                used=False,
            )
        except RatingEligibility.DoesNotExist:
            raise ValidationError(
                _("You are not eligible to rate this agent yet.")
            )
        return eligibility

    @staticmethod
    def _assert_not_already_rated(rater, agent_profile) -> None:
        """Raise ValidationError if the rater has already rated this agent."""
        if AgentRating.objects.filter(rater=rater, agent=agent_profile).exists():
            raise ValidationError(_("You have already rated this agent."))

    @classmethod
    @db_transaction.atomic
    def submit(cls, *, agent_profile, rater, scores: dict, review: str = "") -> AgentRating:
        """Submit a rating for an agent, enforcing eligibility and one-rating-per-user rules."""
        cls._assert_not_already_rated(rater, agent_profile)
        eligibility = cls._assert_eligible(rater, agent_profile)

        rating = AgentRating(
            agent=agent_profile,
            rater=rater,
            review=review,
            **scores,
        )
        rating.save()

        # Mark eligibility as consumed so it can't be reused.
        eligibility.used = True
        eligibility.save(update_fields=["used"])

        return rating

    @classmethod
    def grant_eligibility(cls, *, rater, agent_profile, reason: str) -> "RatingEligibility":
        """
        Call this wherever a meaningful interaction happens
        (enquiry submitted, viewing booked, etc.).

        get_or_create means repeated interactions don't stack up.
        """
        eligibility, _ = RatingEligibility.objects.get_or_create(
            rater=rater,
            agent=agent_profile,
            defaults={"reason": reason},
        )
        return eligibility

    @staticmethod
    def compute_aggregate(agent_profile) -> dict:
        """Compute average scores and total ratings for an agent, rounded to 2 decimals."""
        qs = AgentRating.objects.filter(agent=agent_profile)
        aggregates = qs.aggregate(
            avg_communication=Avg("communication"),
            avg_responsiveness=Avg("responsiveness"),
            avg_professionalism=Avg("professionalism"),
            avg_value_for_money=Avg("value_for_money"),
            avg_overall=Avg("overall"),
            total_ratings=Count("id"),
        )
        return {k: (round(v, 2) if v else None) for k, v in aggregates.items()}
