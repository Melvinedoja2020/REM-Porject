from django.core import signing
from rest_framework import serializers

ONBOARDING_SALT = "bem.onboarding.v1"
ONBOARDING_TOKEN_MAX_AGE = 60 * 60 * 24  # 24 hours


class OnboardingToken:

    @staticmethod
    def generate(user) -> str:
        """Return a signed token encoding user identity."""
        return signing.dumps(
            {"user_id": user.pk, "role": user.role},
            salt=ONBOARDING_SALT,
        )

    @staticmethod
    def verify(token: str) -> dict:
        """
        Verify and decode the token.
        Raises serializers.ValidationError if invalid or expired.
        """
        try:
            data = signing.loads(
                token,
                salt=ONBOARDING_SALT,
                max_age=ONBOARDING_TOKEN_MAX_AGE,
            )
        except signing.SignatureExpired:
            raise serializers.ValidationError(
                {"onboarding_token": "Onboarding session has expired. Please sign up again."}
            )
        except signing.BadSignature:
            raise serializers.ValidationError(
                {"onboarding_token": "Invalid onboarding token."}
            )
        return data
