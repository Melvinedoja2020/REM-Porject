from django.utils.translation import gettext_lazy as _
from rest_framework import HTTP_HEADER_ENCODING
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings

AUTH_HEADER_TYPES = api_settings.AUTH_HEADER_TYPES

if not isinstance(AUTH_HEADER_TYPES, (list, tuple)):
    AUTH_HEADER_TYPES = (AUTH_HEADER_TYPES,)

AUTH_HEADER_TYPE_BYTES = {
    header.encode(HTTP_HEADER_ENCODING) for header in AUTH_HEADER_TYPES
}


class CustomJWTAuthentication(JWTAuthentication):
    """
    Extended JWT authentication class with customized error handling
    and explicit token validation feedback.
    """

    def authenticate(self, request: Request):
        """
        Authenticate the request and return a tuple of:
            (user, validated_token)

        Returns None if no authentication attempt is made.
        """
        header = self.get_header(request)
        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)

        return user, validated_token

    def get_validated_token(self, raw_token):
        """
        Validate the encoded JWT and return a validated token instance.
        Provides detailed feedback for expired or invalid tokens.
        """
        messages = []

        for token_class in api_settings.AUTH_TOKEN_CLASSES:
            try:
                return token_class(raw_token)
            except TokenError as exc:
                messages.append(
                    {
                        "token_class": token_class.__name__,
                        "token_type": token_class.token_type,
                        "message": str(exc),
                    }
                )

        raise InvalidToken(
            {
                "detail": _(
                    "Your session has expired. Please log in again to continue."
                ),
                "messages": messages,
            }
        )

    def get_user(self, validated_token):
        """
        Retrieve and return the user associated with the validated token.
        """
        try:
            user_id = validated_token[api_settings.USER_ID_CLAIM]
        except KeyError:
            raise InvalidToken(
                _("Token contained no recognizable user identification.")
            )

        try:
            user = self.user_model.objects.get(
                **{api_settings.USER_ID_FIELD: user_id}
            )
        except self.user_model.DoesNotExist:
            raise AuthenticationFailed(
                _("User not found."),
                code="user_not_found",
            )

        if not user.is_active:
            raise AuthenticationFailed(
                _("User account is inactive."),
                code="user_inactive",
            )

        return user
