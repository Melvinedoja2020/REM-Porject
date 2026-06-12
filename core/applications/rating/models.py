import auto_prefetch
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.helpers.models import TimeBasedModel

# Create your models here.



class AgentRating(TimeBasedModel):
    """
    A single tenant/buyer rating for an agent, tied to one completed transaction.

    Rules
    -----
    - One rating per (rater, agent) pair — enforced via unique_together.
    - Immutable after creation — no update path is exposed.
    - The overall score is the mean of the four criteria scores, computed on save.
    """

    agent = auto_prefetch.ForeignKey(
        "users.AgentProfile",
        on_delete=models.CASCADE,
        related_name="ratings",
        help_text=_("The agent being rated"),
    )
    rater = auto_prefetch.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="given_ratings",
        help_text=_("The user who submitted the rating"),
    )


    SCORE_VALIDATORS = [MinValueValidator(1), MaxValueValidator(5)]

    communication = models.PositiveSmallIntegerField(
        _("Communication"),
        validators=SCORE_VALIDATORS,
        help_text=_(
            "How well did the agent communicate throughout the transaction?"
        ),
    )
    responsiveness = models.PositiveSmallIntegerField(
        _("Responsiveness"),
        validators=SCORE_VALIDATORS,
        help_text=_("How quickly did the agent respond to inquiries?"),
    )
    professionalism = models.PositiveSmallIntegerField(
        _("Professionalism"),
        validators=SCORE_VALIDATORS,
        help_text=_("How professional was the agent in their interactions?"),
    )
    value_for_money = models.PositiveSmallIntegerField(
        _("Value for Money"),
        validators=SCORE_VALIDATORS,
        help_text=_(
            "How would you rate the overall value of the service provided by the agent?"
        ),
    )

    # ------------------------------------------------------------------
    # Computed overall (mean of criteria, stored for cheap querying)
    # ------------------------------------------------------------------
    overall = models.DecimalField(
        _("Overall Score"),
        max_digits=3,
        decimal_places=2,
        editable=False,   # never set directly
        help_text=_(
            "The average of the four criteria scores, computed automatically."
        ),
    )

    # ------------------------------------------------------------------
    # Optional review text
    # ------------------------------------------------------------------
    review = models.TextField(_("Review"), blank=True)



    class Meta(auto_prefetch.Model.Meta):
        verbose_name = "Agent Rating"
        verbose_name_plural = "Agent Ratings"
        ordering = ["-created_at"]
        unique_together = [("rater", "agent")]  # one rating per rater per agent

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    CRITERIA = ("communication", "responsiveness", "professionalism", "value_for_money")

    def _compute_overall(self) -> float:
        """Compute the overall score as the mean of the criteria."""
        scores = [getattr(self, c) for c in self.CRITERIA]
        return round(sum(scores) / len(scores), 2)

    def clean(self):
        """Validate that all criteria scores are between 1 and 5."""
        for criterion in self.CRITERIA:
            value = getattr(self, criterion, None)
            if value is not None and not (1 <= value <= 5):
                raise ValidationError(
                    {criterion: _("Score must be between 1 and 5.")}
                )

    def save(self, *args, **kwargs):
        """On save, compute the overall score and validate the model."""
        self.overall = self._compute_overall()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Rating by {self.rater_id} for {self.agent_id} — {self.overall}"


class RatingEligibility(TimeBasedModel):
    """
    Tracks whether a user is allowed to rate a specific agent.

    Created when a meaningful interaction occurs (enquiry, property viewing, etc.).
    Destroyed (or marked used) once the rating is submitted.

    Later, this entire model can be replaced by a transaction FK check.
    """

    rater = auto_prefetch.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="rating_eligibilities",
    )
    agent = auto_prefetch.ForeignKey(
        "users.AgentProfile",
        on_delete=models.CASCADE,
        related_name="rating_eligibilities",
    )
    # What earned this eligibility — for auditing.
    reason = models.CharField(
        max_length=100,
        help_text="e.g. 'property_enquiry', 'viewing_completed'",
    )
    used = models.BooleanField(
        default=False,
        help_text="Flipped to True once the rating is submitted.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta(auto_prefetch.Model.Meta):
        verbose_name = "Rating Eligibility"
        verbose_name_plural = "Rating Eligibilities"
        # One active eligibility per rater/agent pair is enough.
        unique_together = [("rater", "agent")]

    def __str__(self):
        status = "used" if self.used else "active"
        return f"{self.rater_id} → {self.agent_id} [{status}]"
