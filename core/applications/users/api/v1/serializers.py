import contextlib
import logging
from typing import Literal

from django.contrib.auth import authenticate
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
from core.applications.users.utils.onboarding_token import OnboardingToken
from core.helpers.custom_exceptions import CustomError
from core.helpers.enums import AgentTypeChoices
from core.helpers.enums import AuthProviderChoices
from core.helpers.enums import GenderChoices
from core.helpers.enums import UserRoleChoice
from core.helpers.enums import VerificationStatusChoices
from core.helpers.interface import BaseModelNoDefs

logger = logging.getLogger(__name__)

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

#----------------------------------------------
# dedicated serializers for schema
# ---------------------------------------------
class GenericMessageSerializer(serializers.Serializer):
    message = serializers.CharField()


class AgentProfessionalDetailsResponseSerializer(serializers.Serializer):
    next_step = serializers.CharField()
    message = serializers.CharField()


class AgentDocumentVerificationResponseSerializer(serializers.Serializer):
    next_step = serializers.CharField()
    message = serializers.CharField()

class OnboardingTokenMixin:
    """
    Mixin for screens 2 & 3.
    Validates the onboarding_token and resolves the AgentProfile instance.
    Subclasses get self._agent_profile after calling validate().
    """

    onboarding_token = serializers.CharField(
        write_only=True,
        help_text="Signed token returned from agent_signup (screen 1).",
    )

    def validate_onboarding_token(self, value: str) -> str:
        """Verify token and attach agent_profile to serializer context."""
        data = OnboardingToken.verify(value)  # raises on invalid/expired

        try:
            agent_profile = AgentProfile.objects.select_related("user").get(
                user_id=data["user_id"],
            )
        except AgentProfile.DoesNotExist:
            msg = "Agent profile not found. Please complete screen 1 first."
            raise serializers.ValidationError(
                msg,
            )

        # Stash on context so the view can access without a second DB hit
        self.context["agent_profile"] = agent_profile
        return value


class CustomerSignupSerializer(serializers.Serializer):
    """
    Register a Customer.
    Supports multiple auth provider flows (email, phone, google) via the
    auth_provider field, which determines required fields and validation logic.
    """

    first_name = serializers.CharField(max_length=150)
    last_name  = serializers.CharField(max_length=150)


    auth_provider = serializers.ChoiceField(
        choices=AuthProviderChoices.choices,
        default=AuthProviderChoices.EMAIL,
        required=False,
    )

    email = serializers.EmailField(
        required=False,
        allow_blank=True,
        help_text="Required for email/phone flows.",
    )
    phone_number = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Required for phone flow. E.164 format e.g. +2348012345678.",
    )
    google_token = serializers.CharField(
        required=False,
        allow_blank=True,
        write_only=True,
    )
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



    def validate_email(self, value: str) -> str:
        """Ensure email is unique if provided."""
        if not value:
            return value
        value = value.strip().lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )
        return value

    def validate_phone_number(self, value: str) -> str:
        """Ensure phone number is unique if provided."""
        if not value:
            return value
        if User.objects.filter(phone_number=value).exists():
            msg = "An account with this phone number already exists."
            raise serializers.ValidationError(
                msg,
            )
        return value



    def _validate_password_fields(self, attrs: dict, errors: dict) -> None:
        """Shared password validation for email and phone flows."""
        pw    = attrs.get("password", "")
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

    def validate(self, attrs: dict) -> dict:
        """Cross-field validation based on auth_provider."""
        provider = attrs.get("auth_provider", AuthProviderChoices.EMAIL)
        errors: dict = {}

        if provider == AuthProviderChoices.EMAIL:
            if not attrs.get("email"):
                errors["email"] = "Email is required."
            self._validate_password_fields(attrs, errors)

        elif provider == AuthProviderChoices.PHONE:
            if not attrs.get("phone_number"):
                errors["phone_number"] = "Phone number is required."
            if not attrs.get("email"):
                errors["email"] = (
                    "Email is required so we can send your activation link."
                )
            self._validate_password_fields(attrs, errors)

        elif provider == AuthProviderChoices.GOOGLE:
            if not attrs.get("google_token"):
                errors["google_token"] = "Google token is required."

        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_user(self, validated_data: dict, role: str) -> User:
        """Construct, save and return a new inactive User."""
        user = User(
            email=validated_data.get("email") or None,
            phone_number=validated_data.get("phone_number") or None,
            first_name_field=validated_data["first_name"].strip(),
            last_name_field=validated_data["last_name"].strip(),
            role=role,
            auth_provider=validated_data["auth_provider"],
            is_active=False,
        )
        user.set_password(validated_data["password"])
        try:
            user.save()
        except Exception as exc:
            logger.exception("Failed to create user: %s", exc)
            raise serializers.ValidationError(
                {"non_field_errors": "Account creation failed. Please try again."}
            )
        return user

    @staticmethod
    def _create_via_google(
        token: str,
        first_name: str,
        last_name: str,
        role: str,
    ) -> User:
        """Stub — replace with real Google ID token verification."""
        raise serializers.ValidationError(
            {"google_token": "Google sign-in is not yet configured on this server."}
        )

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    @transaction.atomic
    def create(self, validated_data: dict) -> dict:
        provider = validated_data["auth_provider"]

        if provider == AuthProviderChoices.GOOGLE:
            user = self._create_via_google(
                token=validated_data["google_token"],
                first_name=validated_data["first_name"].strip(),
                last_name=validated_data["last_name"].strip(),
                role=UserRoleChoice.CUSTOMER,
            )
        else:
            user = self._build_user(validated_data, role=UserRoleChoice.CUSTOMER)

        _, profile_created = UserProfile.objects.get_or_create(
            user=user,
            defaults={"phone_number": user.phone_number},
        )
        logger.info("UserProfile created=%s for user=%s", profile_created, user.pk)

        return {
            "user": UserSerializer.Info(instance=user).data,
            "registration_complete": user.is_active,
            "next_step": "email_activation",
            "message": (
                "Account created successfully. "
                "Please check your email to activate your account."
            ),
        }



class AgentSignupSerializer(CustomerSignupSerializer):
    """
    Register an Agent.
    Inherits all fields and validation from CustomerSignupSerializer,
    but creates an AgentProfile and returns an onboarding_token for the next steps.
    """

    gender = serializers.ChoiceField(
        choices=GenderChoices.choices,
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    date_of_birth = serializers.DateField(
        required=False,
        allow_null=True,
    )

    @transaction.atomic
    def create(self, validated_data: dict) -> dict:
        gender        = validated_data.pop("gender", None)
        date_of_birth = validated_data.pop("date_of_birth", None)
        provider      = validated_data["auth_provider"]

        if provider == AuthProviderChoices.GOOGLE:
            user = self._create_via_google(
                token=validated_data["google_token"],
                first_name=validated_data["first_name"].strip(),
                last_name=validated_data["last_name"].strip(),
                role=UserRoleChoice.AGENT,
            )
        else:
            user = self._build_user(validated_data, role=UserRoleChoice.AGENT)

        profile, created = AgentProfile.objects.update_or_create(
            user=user,
            defaults={
                "gender": gender,
                "date_of_birth": date_of_birth,
                "verified": False,
                "verification_status": VerificationStatusChoices.PENDING,
            },
        )
        logger.info(
            "AgentProfile created=%s id=%s for user=%s",
            created, profile.pk, user.pk,
        )

        # Generate signed onboarding token — valid 24 hrs
        onboarding_token = OnboardingToken.generate(user)

        return {
            "user": UserSerializer.Info(instance=user).data,
            "onboarding_token": onboarding_token,
            "registration_complete": user.is_active,
            "next_step": "professional_details",
            "message": (
                "Account created successfully. "
                "Please check your email to activate your account."
            ),
        }

# ---------------------------------------------------------------------------
class AgentProfessionalDetailsSerializer(
    OnboardingTokenMixin, serializers.ModelSerializer
):
    """
    Update serializer for AgentProfile professional details (screen 2).
    Expects a valid onboarding_token to identify the AgentProfile to update.
        Validates required fields based on agent_type.
    """

    onboarding_token = serializers.CharField(write_only=True)

    class Meta:
        model = AgentProfile
        fields = [
            "onboarding_token",
            "agent_type",
            "office_address",
            "years_of_experience",
            "license_number",
            "office_location",
        ]
        extra_kwargs = {
            "agent_type":           {"required": True},
            "office_address":       {"required": False, "allow_null": True},
            "years_of_experience":  {"required": False, "allow_null": True},
            "license_number":       {"required": False, "allow_null": True},
            "office_location":      {"required": False, "allow_null": True},
        }

    def validate(self, attrs: dict) -> dict:
        """
        Validate required fields based on agent_type.
        For REAL_ESTATE_AGENT, license_number is required.
        For PROPERTY_MANAGER, license_number is optional.
        """

        if (
            attrs.get("agent_type") == AgentTypeChoices.REAL_ESTATE_AGENT
            and not attrs.get("license_number")
        ):
            raise serializers.ValidationError(
                {"license_number": "License number is required for real estate agents."}
            )
        return attrs

    def update(self, instance: AgentProfile, validated_data: dict) -> AgentProfile:
        """Update the AgentProfile with professional details."""
        validated_data.pop("onboarding_token", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        logger.info(
            "AgentProfile professional details updated for user=%s",
            instance.user.pk,
        )
        return instance
class AgentDocumentVerificationSerializer(
    OnboardingTokenMixin, serializers.ModelSerializer
):
    """
    Update serializer for AgentProfile document upload and verification (screen 3).
    Expects a valid onboarding_token to identify the AgentProfile to update.
    Allows uploading license_document and profile_picture,
    and marks the profile as SUBMITTED for admin review.
    """

    onboarding_token = serializers.CharField(write_only=True)
    profile_picture  = serializers.ImageField(
        required=False,
        allow_null=True,
        help_text="Clear selfie photo of the agent.",
    )

    class Meta:
        model = AgentProfile
        fields = [
            "onboarding_token",
            "license_document",
            "profile_picture",
        ]
        extra_kwargs = {
            "license_document": {"required": False, "allow_null": True},
        }

    def update(self, instance: AgentProfile, validated_data: dict) -> AgentProfile:
        validated_data.pop("onboarding_token", None)

        # profile_picture lives on BaseProfile — handle separately
        profile_picture = validated_data.pop("profile_picture", None)
        if profile_picture:
            instance.profile_picture = profile_picture

        for field, value in validated_data.items():
            setattr(instance, field, value)

        # Mark submitted — admin takes over from here
        instance.verification_status = VerificationStatusChoices.SUBMITTED
        instance.save()
        logger.info(
            "AgentProfile documents submitted for user=%s", instance.user.pk
        )
        return instance
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
    email = serializers.EmailField()
    password = serializers.CharField()

    def get_setup_info(self, user: User):
        return {"user_info": user.accounts_dict, "is_verified": user.is_verified}

    def validate(self, attrs):
        authenticate_kwargs = {
            self.username_field: attrs[self.username_field],
            "password": attrs["password"],
        }
        with contextlib.suppress(KeyError):
            authenticate_kwargs["request"] = self.context["request"]

        self.user: User = authenticate(**authenticate_kwargs)
        if not self.user:
            if user := User.objects.filter(email=attrs["email"]).first():
                if not user.is_active:
                    context = {"user": user}
                    to = [get_user_email(user)]
                    settings.EMAIL.activation(self.context["request"], context).send(to)
                    msg = "Your account is not yet verified, kindly check yur email and proceed to verification"  # noqa: E501
                    raise PermissionDenied(
                        msg,
                    )
                if not api_settings.USER_AUTHENTICATION_RULE(self.user):
                    raise AuthenticationFailed(
                        detail="Login failed. Please check your email and password and try again.",
                    )

        data = super().validate(attrs)
        refresh = self.get_token(self.user)
        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)
        data["setup_info"] = None
        data["registration_complete"] = None
        data["setup_info"] = UserSerializer.Info(instance=self.user).data
        data["registration_complete"] = all([self.user.is_active])
        if api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, self.user)
        if not self.user.is_superuser:
            user_logged_in.send(
                sender=self.user.__class__,
                token=data["access"],
                user=self.user,
            )
        return data
