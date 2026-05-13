import contextlib
from typing import Literal

from django.contrib.auth import user_logged_in
from django.contrib.auth.models import update_last_login
from django.contrib.auth.password_validation import validate_password
from django.core import exceptions as django_exceptions
from django.db import transaction
from djoser.compat import get_user_email
from djoser.conf import settings
from djoser.serializers import UserCreateSerializer
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.settings import api_settings

from core.applications.users.models import AgentProfile
from core.applications.users.models import User
from core.applications.users.models import UserProfile
from core.applications.users.token import default_token_generator
from core.helpers.custom_exceptions import CustomError
from core.helpers.enums import AgentTypeChoices
from core.helpers.enums import AuthProviderChoices
from core.helpers.enums import UserRoleChoice
from core.helpers.interface import BaseModelNoDefs

# ---------------------------------------------------------------------------
# Device / OS schemas  (unchanged)
# ---------------------------------------------------------------------------


class OSNameSchema(BaseModelNoDefs):
    Android: Literal["Android"] | None = None
    iOS: Literal["iOS", "iPadOS"] | None = None  # noqa: N815
    web: Literal["iOS", "Windows", "Android"] | None = None


class ModelNameSchema(BaseModelNoDefs):
    Android: str | None = None
    iOS: str | None = None  # noqa: N815
    web: str | None = None


class OSVersionSchema(BaseModelNoDefs):
    Android: str | None = None
    iOS: str | None = None  # noqa: N815
    web: str | None = None


class UserDeviceInfoSchema(BaseModelNoDefs):
    osName: Literal["Android", "android", "iOS", "ios", "web", "Web"] | None = None
    modelName: str | None = None  # noqa: N815
    osVersion: str | None = None  # noqa: N815


class UserMetadataSchema(BaseModelNoDefs):
    push_notification_id: str | None
    device_info: UserDeviceInfoSchema | None


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _build_token_pair(user: User) -> dict:
    """
    Return a fresh access + refresh JWT pair for *user*.

    Respects SIMPLE_JWT settings (lifetime, header type, etc.) because
    RefreshToken.for_user() reads from the same simplejwt configuration.

    Used in signup flows to log the user in immediately after creation
    so the frontend can store tokens while the user checks their email.
    """
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


# ---------------------------------------------------------------------------
# User read serializers  (extended)
# ---------------------------------------------------------------------------


class CustomUserSerializer(serializers.ModelSerializer):
    """
    Read serializer — wired via DJOSER['SERIALIZERS']['user'].
    Extended to include all fields present on the updated User model.
    """

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "first_name_field",
            "last_name_field",
            "email",
            "phone_number",
            "role",
            "auth_provider",
            "is_email_verified",
            "is_phone_verified",
            "is_active",
        ]
        read_only_fields = fields


class GetUser(serializers.ModelSerializer):
    """
    Thin read serializer — wired via DJOSER['SERIALIZERS']['current_user'].
    Unchanged from original.
    """

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "is_active",
        )


# ---------------------------------------------------------------------------
# UserSerializer namespace  (preserved + Info extended)
# ---------------------------------------------------------------------------


class UserSerializer:

    class AddOrRetrieveDevice(serializers.ModelSerializer):
        class Meta:
            model = User
            fields = ("email",)

    class Update(serializers.ModelSerializer):
        class Meta:
            model = User
            fields = ("email",)

    class Info(serializers.ModelSerializer):
        """
        Enriched snapshot returned inside every auth response.

        Extended from the original shape to include the fields the
        frontend needs to drive the post-auth UI without a second call.
        Keeps setup_info key in CustomTokenObtainPairSerializer for
        backwards compatibility.
        """

        full_name = serializers.SerializerMethodField(read_only=True)

        class Meta:
            model = User
            fields = (
                "id",
                "email",
                "phone_number",
                "full_name",
                "name",
                "first_name_field",
                "last_name_field",
                "role",
                "auth_provider",
                "is_email_verified",
                "is_phone_verified",
            )
            read_only_fields = fields

        def get_full_name(self, obj: User) -> str:
            return obj.get_full_name()


# ---------------------------------------------------------------------------
# Customer signup  (NEW)
# ---------------------------------------------------------------------------


class CustomerSignupSerializer(serializers.Serializer):
    """
    Register a Buyer / Renter.
    Wired via DJOSER['SERIALIZERS']['customer_signup'].

    Auth provider flows
    -------------------
    email  → first_name, last_name, email, password, re_password
    phone  → first_name, last_name, phone_number, email, password, re_password
             (email still required so djoser ActivationEmail can be sent)
    google → first_name, last_name, google_token
             (user created active — no email needed)

    In all non-Google flows the account is created inactive and the
    djoser ActivationEmail is dispatched by the view using the same
    settings.EMAIL.activation path that the rest of the app uses.

    Response
    --------
    {
        "access":                "<jwt>",
        "refresh":               "<jwt>",
        "user":                  { UserSerializer.Info },
        "registration_complete": bool
    }
    """

    # --- Identity ---
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)

    # --- Flow selector ---
    auth_provider = serializers.ChoiceField(
        choices=AuthProviderChoices.choices,
        default=AuthProviderChoices.EMAIL,
    )

    # --- Email (required for email flow; also used for phone flow
    #     so the activation email has a destination) ---
    email = serializers.EmailField(
        required=False,
        allow_blank=True,
        help_text=(
            "Required for email flow. "
            "For phone flow, provide so the activation email can be sent."
        ),
    )

    # --- Phone (required for phone flow) ---
    phone_number = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Required for phone flow. E.164 format, e.g. +2348012345678.",
    )

    # --- Google ---
    google_token = serializers.CharField(
        required=False,
        allow_blank=True,
        write_only=True,
    )

    # --- Password ---
    password = serializers.CharField(
        style={"input_type": "password"},
        write_only=True,
        required=False,
    )
    re_password = serializers.CharField(
        style={"input_type": "password"},
        write_only=True,
        required=False,
    )

    # ------------------------------------------------------------------
    # Field-level validation
    # ------------------------------------------------------------------

    def validate_email(self, value: str) -> str:
        if not value:
            return value
        value = value.strip().lower()
        if User.objects.filter(email=value).exists():
            msg = "An account with this email already exists."
            raise serializers.ValidationError(
                msg,
            )
        return value

    def validate_phone_number(self, value: str) -> str:
        if not value:
            return value
        if User.objects.filter(phone_number=value).exists():
            msg = "An account with this phone number already exists."
            raise serializers.ValidationError(
                msg,
            )
        return value

    # ------------------------------------------------------------------
    # Cross-field validation
    # ------------------------------------------------------------------

    def validate(self, attrs: dict) -> dict:
        provider = attrs.get("auth_provider", AuthProviderChoices.EMAIL)
        errors = {}

        if provider == AuthProviderChoices.EMAIL:
            if not attrs.get("email"):
                errors["email"] = "Email is required."

            pw = attrs.get("password", "")
            re_pw = attrs.get("re_password", "")
            if not pw:
                errors["password"] = "Password is required."
            elif not re_pw:
                errors["re_password"] = "Please confirm your password."
            elif pw != re_pw:
                errors["re_password"] = "Passwords do not match."
            else:
                try:
                    validate_password(pw)
                except django_exceptions.ValidationError as exc:
                    errors["password"] = exc.messages[0]

        elif provider == AuthProviderChoices.PHONE:
            if not attrs.get("phone_number"):
                errors["phone_number"] = "Phone number is required."
            # Email still needed so djoser can send the activation link
            if not attrs.get("email"):
                errors["email"] = (
                    "Email is required so we can send your activation link."
                )

            pw = attrs.get("password", "")
            re_pw = attrs.get("re_password", "")
            if not pw:
                errors["password"] = "Password is required."
            elif not re_pw:
                errors["re_password"] = "Please confirm your password."
            elif pw != re_pw:
                errors["re_password"] = "Passwords do not match."
            else:
                try:
                    validate_password(pw)
                except django_exceptions.ValidationError as exc:
                    errors["password"] = exc.messages[0]

        elif provider == AuthProviderChoices.GOOGLE:
            if not attrs.get("google_token"):
                errors["google_token"] = "Google token is required."

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    @transaction.atomic
    def create(self, validated_data: dict) -> dict:
        provider = validated_data["auth_provider"]
        first_name = validated_data["first_name"].strip()
        last_name = validated_data["last_name"].strip()

        if provider == AuthProviderChoices.GOOGLE:
            user = self._create_via_google(
                token=validated_data["google_token"],
                first_name=first_name,
                last_name=last_name,
                role=UserRoleChoice.CUSTOMER,
            )
        else:
            user = User(
                email=validated_data.get("email") or None,
                phone_number=validated_data.get("phone_number") or None,
                first_name_field=first_name,
                last_name_field=last_name,
                role=UserRoleChoice.CUSTOMER,
                auth_provider=provider,
                is_active=False,  # activated via djoser email link
            )
            user.set_password(validated_data["password"])
            user.save()

        # Create UserProfile atomically — idempotent so safe on retries
        UserProfile.objects.get_or_create(
            user=user,
            defaults={"phone_number": user.phone_number},
        )

        return {
            "user": UserSerializer.Info(instance=user).data,
            "registration_complete": user.is_active,
            "message": "Account created successfully. Please check your email to activate your account.",
        }

    @staticmethod
    def _create_via_google(
        token: str,
        first_name: str,
        last_name: str,
        role: str,
    ) -> User:
        """
        Verify a Google ID token and return (or create) the matching User.

        TODO: replace stub with real verification once Google client ID
        is configured:

            from google.oauth2 import id_token
            from google.auth.transport import requests as g_requests
            from django.conf import settings as django_settings

            idinfo = id_token.verify_oauth2_token(
                token,
                g_requests.Request(),
                django_settings.GOOGLE_CLIENT_ID,
            )
            email = idinfo["email"]
        """
        raise serializers.ValidationError(
            {"google_token": "Google sign-in is not yet configured on this server."}
        )


# ---------------------------------------------------------------------------
# Agent signup  (NEW)
# ---------------------------------------------------------------------------


class AgentSignupSerializer(CustomerSignupSerializer):
    """
    Register an Agent / Landlord.
    Wired via DJOSER['SERIALIZERS']['agent_signup'].

    Extends CustomerSignupSerializer with agent_type.
    Same email activation flow — djoser ActivationEmail is sent by the view.

    Document uploads (license_document, company_registration_document)
    are handled via PATCH /agent-profile/{id}/ after account creation
    to keep the signup form simple.
    """

    agent_type = serializers.ChoiceField(
        choices=AgentTypeChoices.choices,
        help_text="Agent classification — determines required profile fields.",
    )

    @transaction.atomic
    def create(self, validated_data: dict) -> dict:
        # Pop agent_type before passing to parent logic
        agent_type = validated_data.pop("agent_type")
        provider = validated_data["auth_provider"]
        first_name = validated_data["first_name"].strip()
        last_name = validated_data["last_name"].strip()

        if provider == AuthProviderChoices.GOOGLE:
            user = self._create_via_google(
                token=validated_data["google_token"],
                first_name=first_name,
                last_name=last_name,
                role=UserRoleChoice.AGENT,
            )
        else:
            user = User(
                email=validated_data.get("email") or None,
                phone_number=validated_data.get("phone_number") or None,
                first_name_field=first_name,
                last_name_field=last_name,
                role=UserRoleChoice.AGENT,
                auth_provider=provider,
                is_active=False,
            )
            user.set_password(validated_data["password"])
            user.save()

        AgentProfile.objects.get_or_create(
            user=user,
            defaults={"agent_type": agent_type},
        )

        return {
            "user": UserSerializer.Info(instance=user).data,
            "registration_complete": user.is_active,
            "message": "Account created successfully. Please check your email to activate your account.",
        }


# ---------------------------------------------------------------------------
# Legacy djoser create serializer  (unchanged)
# ---------------------------------------------------------------------------


class CustomUserCreateSerializer(UserCreateSerializer):
    """
    Kept for DJOSER['SERIALIZERS']['user_create'] config key.
    Prefer CustomerSignupSerializer / AgentSignupSerializer for signup.
    """

    re_password = serializers.CharField(
        style={"input_type": "password"},
        required=True,
        write_only=True,
    )

    def validate(self, attrs):
        re_password = attrs.pop("re_password")
        attrs = super().validate(attrs)
        password = attrs.get("password")

        if password != re_password:
            msg = "The passwords entered do not match."
            raise CustomError.BadRequest({"re_password": msg})
        return attrs

    class Meta(UserCreateSerializer.Meta):
        fields = (
            "name",
            "role",
            "email",
            "password",
            "re_password",
        )
        extra_kwargs = {
            "re_password": {"write_only": True},
        }


# ---------------------------------------------------------------------------
# Password serializers  (unchanged)
# ---------------------------------------------------------------------------


class PasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(style={"input_type": "password"})

    def validate(self, attrs):
        user = getattr(self, "user", None) or self.context["request"].user
        assert user is not None  # noqa: S101

        try:
            validate_password(attrs["new_password"], user)
        except django_exceptions.ValidationError as e:
            raise CustomError.BadRequest({"new_password": e.messages[0]})  # noqa: B904
        return super().validate(attrs)


class PasswordRetypeSerializer(PasswordSerializer):
    re_new_password = serializers.CharField(style={"input_type": "password"})

    default_error_messages = {
        "password_mismatch": settings.CONSTANTS.messages.PASSWORD_MISMATCH_ERROR,
    }

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if attrs["new_password"] == attrs["re_new_password"]:
            return attrs
        return self.fail("password_mismatch")


# ---------------------------------------------------------------------------
# Username serializers  (unchanged)
# ---------------------------------------------------------------------------


class UsernameSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (settings.LOGIN_FIELD,)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.username_field = settings.LOGIN_FIELD
        self._default_username_field = User.USERNAME_FIELD
        self.fields[f"new_{self.username_field}"] = self.fields.pop(self.username_field)

    def save(self, **kwargs):
        if self.username_field != self._default_username_field:
            kwargs[User.USERNAME_FIELD] = self.validated_data.get(
                f"new_{self.username_field}",
            )
        return super().save(**kwargs)


class UsernameRetypeSerializer(UsernameSerializer):
    default_error_messages = {
        "username_mismatch": settings.CONSTANTS.messages.USERNAME_MISMATCH_ERROR.format(
            settings.LOGIN_FIELD,
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["re_new_" + settings.LOGIN_FIELD] = serializers.CharField()

    def validate(self, attrs):
        attrs = super().validate(attrs)
        new_username = attrs[settings.LOGIN_FIELD]
        if new_username != attrs[f"re_new_{settings.LOGIN_FIELD}"]:
            return self.fail("username_mismatch")
        return attrs


# ---------------------------------------------------------------------------
# Activation & token serializers  (unchanged)
# ---------------------------------------------------------------------------


class EmailAndTokenSerializer(serializers.Serializer):
    email = serializers.EmailField()
    token = serializers.CharField()

    default_error_messages = {
        "invalid_token": "The token may have expired or is invalid.",
        "invalid_email": "No user found with that email. Create an account or try another email.",
    }

    def validate(self, attrs):
        validated_data = super().validate(attrs)

        try:
            email = self.initial_data.get("email", "")
            self.user = User.objects.get(email=email)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError) as e:
            key_error = "invalid_email"
            raise CustomError.BadRequest(
                {"email": self.error_messages[key_error]},
                code=key_error,
            ) from e

        is_token_valid = default_token_generator.check_token(
            self.user,
            self.initial_data.get("token", ""),
        )
        if is_token_valid:
            return validated_data
        key_error = "invalid_token"
        raise CustomError.BadRequest(
            {"token": self.error_messages[key_error]},
            code=key_error,
        )


class ActivationSerializer(EmailAndTokenSerializer):
    """
    Handles user activation and returns JWT tokens.
    """

    default_error_messages = {
        "stale_token": settings.CONSTANTS.messages.STALE_TOKEN_ERROR,
    }

    def validate(self, attrs):
        attrs = super().validate(attrs)

        if self.user.is_active:
            raise PermissionDenied(self.error_messages["stale_token"])

        return attrs

    def save(self, **kwargs):
        """
        Activate user and return JWT tokens.
        """
        # Activate user
        self.user.is_active = True
        self.user.is_email_verified = True
        self.user.save(update_fields=["is_active", "is_email_verified"])

        # Generate tokens
        tokens = _build_token_pair(self.user)

        return {
            **tokens,
            "user": UserSerializer.Info(instance=self.user).data,
            "message": "Account activated successfully.",
        }


class PasswordResetConfirmSerializer(EmailAndTokenSerializer, PasswordSerializer):
    pass


class PasswordResetConfirmRetypeSerializer(
    EmailAndTokenSerializer,
    PasswordRetypeSerializer,
):
    pass


class UsernameResetConfirmSerializer(EmailAndTokenSerializer, UsernameSerializer):
    pass


class UsernameResetConfirmRetypeSerializer(
    EmailAndTokenSerializer,
    UsernameRetypeSerializer,
):
    pass


# ---------------------------------------------------------------------------
# Login — email OR phone  (extended)
# ---------------------------------------------------------------------------


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Extends simplejwt's TokenObtainPairSerializer to accept login via
    email address OR phone number via a single ``credential`` field.

    Wired via SIMPLE_JWT['TOKEN_OBTAIN_SERIALIZER'].

    Inactive account handling
    -------------------------
    - email provider  → resends djoser ActivationEmail automatically
    - phone provider  → same: resends to the email on the account
    - google provider → should never be inactive; surfaces a generic error

    Response (shape preserved from original)
    -----------------------------------------
    {
        "refresh":               "<jwt>",
        "access":                "<jwt>",
        "setup_info":            { UserSerializer.Info },
        "registration_complete": bool
    }
    """

    # Replace parent's email-only field with a generic credential field
    email = None  # type: ignore[assignment]
    credential = serializers.CharField(
        help_text="Email address or phone number used during signup."
    )
    password = serializers.CharField(style={"input_type": "password"})

    def _resolve_user(self, credential: str) -> User | None:
        """Return the User whose email or phone matches credential."""
        from django.db.models import Q

        return User.objects.filter(
            Q(email=credential) | Q(phone_number=credential)
        ).first()

    def validate(self, attrs: dict) -> dict:
        credential = attrs.get("credential", "").strip()
        password = attrs.get("password", "")

        user = self._resolve_user(credential)

        if not user:
            raise AuthenticationFailed(
                "No account found with these credentials. Please check and try again."
            )

        # Inactive → resend djoser activation email and surface a clear message
        if not user.is_active:
            if user.email:
                context = {"user": user}
                to = [get_user_email(user)]
                with contextlib.suppress(Exception):
                    settings.EMAIL.activation(
                        self.context["request"], context
                    ).send(to)
            raise PermissionDenied(
                "Your account is not yet verified. "
                "Please check your email and click the activation link."
            )

        if not user.check_password(password):
            raise AuthenticationFailed("Incorrect password. Please try again.")

        if not api_settings.USER_AUTHENTICATION_RULE(user):
            raise AuthenticationFailed(
                "Login failed. Your account may have been suspended."
            )

        self.user = user

        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(user)
        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            # setup_info key preserved for backwards compatibility
            "setup_info": UserSerializer.Info(instance=user).data,
            "registration_complete": user.is_active,
        }

        if api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, user)

        if not user.is_superuser:
            user_logged_in.send(
                sender=user.__class__,
                token=data["access"],
                user=user,
            )

        return data
