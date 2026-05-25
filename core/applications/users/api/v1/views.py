import logging
from smtplib import SMTPRecipientsRefused

from django.contrib.auth import logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import user_logged_out
from django.utils.module_loading import import_string
from django.utils.timezone import now
from djoser import signals
from djoser import utils
from djoser.compat import get_user_email
from djoser.conf import settings
from djoser.email import ActivationEmail
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.parsers import FormParser
from rest_framework.parsers import JSONParser
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.authentication import AUTH_HEADER_TYPES
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings

from core.applications.users.api.v1.schema.auth_schema import JWT_LOGIN_SCHEMA
from core.applications.users.api.v1.schema.auth_schema import JWT_REFRESH_SCHEMA
from core.applications.users.api.v1.schema.auth_schema import JWT_VERIFY_SCHEMA
from core.applications.users.api.v1.schema.users import user_schema
from core.applications.users.models import User
from core.applications.users.token import default_token_generator
from core.helpers.custom_exceptions import CustomError

from .serializers import AgentDocumentVerificationSerializer
from .serializers import AgentProfessionalDetailsSerializer
from .serializers import UserSerializer

# setup logging
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Token views  (unchanged from original)
# ---------------------------------------------------------------------------


class AuthView(ModelViewSet):
    model = ActivationEmail


class TokenViewBase(generics.GenericAPIView):
    permission_classes = ()
    authentication_classes = ()
    parser_classes = [MultiPartParser, JSONParser]

    serializer_class = None
    _serializer_class = ""

    www_authenticate_realm = "api"

    def get_serializer_class(self):
        """
        If serializer_class is set, use it directly.
        Otherwise get the class from settings.
        """
        if self.serializer_class:
            return self.serializer_class
        try:
            return import_string(self._serializer_class)
        except ImportError as err:
            msg = f"Could not import serializer '{self._serializer_class}'"
            raise ImportError(msg) from err

    def get_authenticate_header(self, request):
        return f'{AUTH_HEADER_TYPES[0]} realm="{self.www_authenticate_realm}"'

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0]) from e

        return Response(serializer.validated_data, status=status.HTTP_200_OK)

@JWT_LOGIN_SCHEMA
class TokenObtainPairView(TokenViewBase):
    """
    Takes a credential (email or phone) + password and returns an
    access / refresh JWT pair to prove authentication.
    """

    _serializer_class = api_settings.TOKEN_OBTAIN_SERIALIZER


token_obtain_pair = TokenObtainPairView.as_view()


class TokenObtainSlidingView(TokenViewBase):
    _serializer_class = api_settings.SLIDING_TOKEN_OBTAIN_SERIALIZER


token_obtain_sliding = TokenObtainSlidingView.as_view()


class TokenRefreshSlidingView(TokenViewBase):
    _serializer_class = api_settings.SLIDING_TOKEN_REFRESH_SERIALIZER


token_refresh_sliding = TokenRefreshSlidingView.as_view()

@JWT_REFRESH_SCHEMA
class TokenRefreshView(TokenViewBase):
    _serializer_class = api_settings.TOKEN_REFRESH_SERIALIZER


token_refresh = TokenRefreshView.as_view()

@JWT_VERIFY_SCHEMA
class TokenVerifyView(TokenViewBase):
    _serializer_class = api_settings.TOKEN_VERIFY_SERIALIZER


token_verify = TokenVerifyView.as_view()


class TokenBlacklistView(TokenViewBase):
    _serializer_class = api_settings.TOKEN_BLACKLIST_SERIALIZER


token_blacklist = TokenBlacklistView.as_view()


# ---------------------------------------------------------------------------
# UserViewSet
# ---------------------------------------------------------------------------

@user_schema
@extend_schema(tags=["User"])
class UserViewSet(ModelViewSet):
    serializer_class = settings.SERIALIZERS.user
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]
    token_generator = default_token_generator
    lookup_field = settings.USER_ID_FIELD
    parser_classes = [MultiPartParser, JSONParser, FormParser]

    def permission_denied(self, request, *args, **kwargs):
        if (
            settings.HIDE_USERS
            and request.user.is_authenticated
            and self.action in ["update", "partial_update", "list", "retrieve"]
        ):
            raise NotFound
        super().permission_denied(request, **kwargs)

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        if settings.HIDE_USERS and self.action == "list" and not user.is_staff:
            queryset = queryset.filter(pk=user.pk)
        return queryset

    # ------------------------------------------------------------------
    # get_permissions — extended with customer_signup + agent_signup
    # ------------------------------------------------------------------

    def get_permissions(self):
        """
        Defines the permission classes for the UserViewSet based on the
        current action.

        Original actions (unchanged):
            create, activation, resend_activation, list, reset_password,
            reset_password_confirm, set_password, set_username,
            reset_username, reset_username_confirm, destroy / me DELETE

        New actions:
            customer_signup  → settings.PERMISSIONS.customer_signup
            agent_signup     → settings.PERMISSIONS.agent_signup
        """
        if self.action == "create":
            self.permission_classes = settings.PERMISSIONS.user_create
        elif self.action == "activation":
            self.permission_classes = settings.PERMISSIONS.activation
        elif self.action == "resend_activation":
            self.permission_classes = settings.PERMISSIONS.password_reset
        elif self.action == "list":
            self.permission_classes = settings.PERMISSIONS.user_list
        elif self.action == "reset_password":
            self.permission_classes = settings.PERMISSIONS.password_reset
        elif self.action == "reset_password_confirm":
            self.permission_classes = settings.PERMISSIONS.password_reset_confirm
        elif self.action == "set_password":
            self.permission_classes = settings.PERMISSIONS.set_password
        elif self.action == "set_username":
            self.permission_classes = settings.PERMISSIONS.set_username
        elif self.action == "reset_username":
            self.permission_classes = settings.PERMISSIONS.username_reset
        elif self.action == "reset_username_confirm":
            self.permission_classes = settings.PERMISSIONS.username_reset_confirm
        elif self.action == "destroy" or (
            self.action == "me" and self.request and self.request.method == "DELETE"
        ):
            self.permission_classes = settings.PERMISSIONS.user_delete
        # --- NEW ---
        # elif self.action == "customer_signup":
        #     self.permission_classes = settings.PERMISSIONS.customer_signup
        # elif self.action == "agent_signup":
        #     self.permission_classes = settings.PERMISSIONS.agent_signup
        # return super().get_permissions()
        elif self.action in (
            "customer_signup", "agent_signup",
            "agent_professional_details", "agent_document_verification"
        ):
            self.permission_classes = [AllowAny]

        return super().get_permissions()

    # ------------------------------------------------------------------
    # get_serializer_class — extended with customer_signup + agent_signup
    # ------------------------------------------------------------------

    def get_serializer_class(self):
        """
        Returns the serializer class to use in the view.

        Original actions (unchanged):
            create, destroy, activation, resend_activation,
            reset_password, reset_password_confirm, set_password,
            set_username, reset_username, reset_username_confirm, me

        New actions:
            customer_signup  → settings.SERIALIZERS.customer_signup
            agent_signup     → settings.SERIALIZERS.agent_signup
        """
        if self.action == "create":
            if settings.USER_CREATE_PASSWORD_RETYPE:
                return settings.SERIALIZERS.user_create_password_retype
            return settings.SERIALIZERS.user_create
        if self.action == "destroy" or (
            self.action == "me" and self.request and self.request.method == "DELETE"
        ):
            return settings.SERIALIZERS.user_delete
        if self.action == "activation":
            return settings.SERIALIZERS.activation
        if self.action == "resend_activation" or self.action == "reset_password":
            return settings.SERIALIZERS.password_reset
        if self.action == "reset_password_confirm":
            if settings.PASSWORD_RESET_CONFIRM_RETYPE:
                return settings.SERIALIZERS.password_reset_confirm_retype
            return settings.SERIALIZERS.password_reset_confirm
        if self.action == "set_password":
            if settings.SET_PASSWORD_RETYPE:
                return settings.SERIALIZERS.set_password_retype
            return settings.SERIALIZERS.set_password
        if self.action == "set_username":
            if settings.SET_USERNAME_RETYPE:
                return settings.SERIALIZERS.set_username_retype
            return settings.SERIALIZERS.set_username
        if self.action == "reset_username":
            return settings.SERIALIZERS.username_reset
        if self.action == "reset_username_confirm":
            if settings.USERNAME_RESET_CONFIRM_RETYPE:
                return settings.SERIALIZERS.username_reset_confirm_retype
            return settings.SERIALIZERS.username_reset_confirm
        if self.action == "me":
            return settings.SERIALIZERS.current_user
        # --- NEW ---
        if self.action == "customer_signup":
            return settings.SERIALIZERS.customer_signup
        if self.action == "agent_signup":
            return settings.SERIALIZERS.agent_signup

        return self.serializer_class

    def get_instance(self):
        return self.request.user

    # ------------------------------------------------------------------
    #  customer_signup
    # ------------------------------------------------------------------

    @action(["post"], detail=False)
    def customer_signup(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.create(serializer.validated_data)

        # Re-fetch to fire signals and send activation email
        user: User = User.objects.get(id=result["user"]["id"])

        signals.user_registered.send(
            sender=self.__class__,
            user=user,
            request=request,
        )

        # Use the same djoser activation email path as perform_create
        self._send_activation_email(request, user)

        return Response(result, status=status.HTTP_201_CREATED)

    # ------------------------------------------------------------------


    @action(["post"], detail=False, url_path="agent_signup")
    def agent_signup(self, request: Request, *args, **kwargs) -> Response:
        """
        Agent signup flow:
        1. Create user with is_active=False
        2. Send activation email
        3. After activation, agent fills professional details (screen 2)
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.create(serializer.validated_data)

        user: User = User.objects.get(id=result["user"]["id"])

        signals.user_registered.send(
            sender=self.__class__,
            user=user,
            request=request,
        )
        self._send_activation_email(request, user)

        return Response(result, status=status.HTTP_201_CREATED)

    # ------------------------------------------------------------------
    # Private: activation email dispatcher
    # ------------------------------------------------------------------

    def _send_activation_email(self, request: Request, user: User) -> None:
        """
        Send the djoser ActivationEmail to *user* using the same path
        as perform_create — settings.EMAIL.activation.

        Skipped for Google accounts (already active).
        Logs SMTP failures rather than crashing the signup response.
        """
        if user.is_active:
            # Google flow — user already verified, nothing to send
            return

        if not user.email:
            # Should not happen given our validation, but guard anyway
            logger.warning(
                "Skipping activation email for user %s — no email address.", user.pk
            )
            return

        context = {"user": user}
        to = [get_user_email(user)]
        logger.info("Sending activation email to %s", to)
        try:
            if settings.SEND_ACTIVATION_EMAIL:
                settings.EMAIL.activation(request, context).send(to)
            elif settings.SEND_CONFIRMATION_EMAIL:
                settings.EMAIL.confirmation(request, context).send(to)
            logger.info("Activation email sent to %s", to)
        except SMTPRecipientsRefused as exc:
            logger.error("SMTPRecipientsRefused sending to %s: %s", to, exc)
            raise CustomError.EmailSendError(
                "Unable to send the activation email. Please contact support."
            )

    @action(["patch"], detail=False, url_path="agent_professional_details")
    def agent_professional_details(self, request: Request, *args, **kwargs) -> Response:
        """
        Screen 2 of agent onboarding — professional details.
        Called after email activation. Requires onboarding token for authentication.
        """
        serializer = AgentProfessionalDetailsSerializer(
            data=request.data,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)

        # Agent profile was stashed on context by OnboardingTokenMixin
        agent_profile = serializer.context["agent_profile"]
        serializer.update(agent_profile, serializer.validated_data)

        return Response(
            {
                "next_step": "document_verification",
                "message": "Professional details saved successfully.",
            },
            status=status.HTTP_200_OK,
        )


    @action(["patch"], detail=False, url_path="agent_document_verification")
    def agent_document_verification(self, request: Request, *args, **kwargs) -> Response:
        """
        Screen 3 — Document uploads.

        Multipart form data.
        Resolves agent via onboarding_token.
        Sets verification_status = SUBMITTED on success.
        """
        serializer = AgentDocumentVerificationSerializer(
            data=request.data,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)

        agent_profile = serializer.context["agent_profile"]
        serializer.update(agent_profile, serializer.validated_data)

        return Response(
            {
                "next_step": "complete",
                "message": (
                    "Documents submitted successfully. "
                    "Your account is under review."
                ),
            },
            status=status.HTTP_200_OK,
        )
    # @create_schema
    def perform_create(self, serializer, *args, **kwargs):
        """
        Handles the creation of a new user instance.

        Saves the user instance using the provided serializer
        and triggers the user_registered signal.

        Parameters:
            serializer (Serializer): The serializer instance
            used to create the user.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            None
        """
        user = serializer.save(*args, **kwargs)
        signals.user_registered.send(
            sender=self.__class__,
            user=user,
            request=self.request,
        )

        context = {"user": user}
        to = [get_user_email(user)]
        print("Sending email...")
        try:
            if settings.SEND_ACTIVATION_EMAIL:
                settings.EMAIL.activation(self.request, context).send(to)
            elif settings.SEND_CONFIRMATION_EMAIL:
                settings.EMAIL.confirmation(self.request, context).send(to)
            print("Email sent!")
        except SMTPRecipientsRefused as smtp_error:
            logger.error("SMTPRecipientsRefused: %s", smtp_error)
            raise CustomError.EmailSendError("Unable to send email. Please contact support.")

    @action(
        detail=False,
        methods=["get"],
        url_path="email/(?P<email>.+)",
        url_name="get-by-email",
    )
    def get_by_email(self, request, email=None):
        """
        Custom endpoint to retrieve a user by email.
        Usage: /users/email/<email>/
        """
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise NotFound("User with this email does not exist.")

        serializer = self.get_serializer(user)
        return Response(serializer.data)

    def perform_update(self, serializer, *args, **kwargs):
        """
        Handles the update of an existing user instance.

        Saves the user instance using the provided serializer
        and triggers the user_updated signal.

        Parameters:
            serializer (Serializer): The serializer instance
            used to update the user.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            None
        """
        super().perform_update(serializer, *args, **kwargs)
        user = serializer.instance
        signals.user_updated.send(
            sender=self.__class__,
            user=user,
            request=self.request,
        )

        # should we send activation email after update?
        if settings.SEND_ACTIVATION_EMAIL and not user.is_active:
            context = {"user": user}
            to = [get_user_email(user)]
            settings.EMAIL.activation(self.request, context).send(to)

    def destroy(self, request, *args, **kwargs):
        """
        Handles the deletion of an existing user instance.

        Parameters:
            request: The request object.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            A response with a status code of 204 (No Content)
            indicating the deletion was successful.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)

        if instance == request.user:
            utils.logout_user(self.request)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(["get", "put", "patch", "delete"], detail=False)
    def me(self, request, *args, **kwargs):
        self.get_object = self.get_instance
        if request.method == "GET":
            return self.retrieve(request, *args, **kwargs)
        if request.method == "PUT":
            return self.update(request, *args, **kwargs)
        if request.method == "PATCH":
            return self.partial_update(request, *args, **kwargs)
        if request.method == "DELETE":
            return self.destroy(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(["post"], detail=False)
    def activation(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data,
            context={"request": request},  # good practice
        )
        serializer.is_valid(raise_exception=True)

        data = serializer.save()
        user = serializer.user
        signals.user_activated.send(
            sender=self.__class__,
            user=user,
            request=self.request,
        )

        if settings.SEND_CONFIRMATION_EMAIL:
            context = {"user": user}
            to = [get_user_email(user)]
            settings.EMAIL.confirmation(self.request, context).send(to)

        return Response(data, status=status.HTTP_200_OK)

    @action(["post"], detail=False)
    def resend_activation(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.get_user(is_active=False)

        if not settings.SEND_ACTIVATION_EMAIL or not user:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        context = {"user": user}
        to = [get_user_email(user)]
        settings.EMAIL.activation(self.request, context).send(to)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(["post"], detail=False)
    def set_password(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        self.request.user.set_password(serializer.data["new_password"])
        self.request.user.save()

        if settings.PASSWORD_CHANGED_EMAIL_CONFIRMATION:
            context = {"user": self.request.user}
            to = [get_user_email(self.request.user)]
            settings.EMAIL.password_changed_confirmation(self.request, context).send(to)

        if settings.LOGOUT_ON_PASSWORD_CHANGE:
            utils.logout_user(self.request)
        elif settings.CREATE_SESSION_ON_LOGIN:
            update_session_auth_hash(self.request, self.request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(["post"], detail=False)
    def reset_password(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.get_user()

        if user:
            context = {"user": user}
            to = [get_user_email(user)]
            settings.EMAIL.password_reset(self.request, context).send(to)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(["post"], detail=False)
    def reset_password_confirm(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.user.set_password(serializer.data["new_password"])
        if hasattr(serializer.user, "last_login"):
            serializer.user.last_login = now()
        serializer.user.save()

        if settings.PASSWORD_CHANGED_EMAIL_CONFIRMATION:
            context = {"user": serializer.user}
            to = [get_user_email(serializer.user)]
            settings.EMAIL.password_changed_confirmation(self.request, context).send(to)
            print("password reseted")
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(["post"], detail=False, url_path=f"set_{User.USERNAME_FIELD}")
    def set_username(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self.request.user
        new_username = serializer.data["new_" + User.USERNAME_FIELD]

        setattr(user, User.USERNAME_FIELD, new_username)
        user.save()
        if settings.USERNAME_CHANGED_EMAIL_CONFIRMATION:
            context = {"user": user}
            to = [get_user_email(user)]
            settings.EMAIL.username_changed_confirmation(self.request, context).send(to)

    @action(["post"], detail=False, url_path=f"reset_{User.USERNAME_FIELD}")
    def reset_username(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.get_user()

        if user:
            context = {"user": user}
            to = [get_user_email(user)]
            settings.EMAIL.username_reset(self.request, context).send(to)

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(["post"], detail=False, url_path=f"reset_{User.USERNAME_FIELD}_confirm")
    def reset_username_confirm(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_username = serializer.data["new_" + User.USERNAME_FIELD]

        setattr(serializer.user, User.USERNAME_FIELD, new_username)
        if hasattr(serializer.user, "last_login"):
            serializer.user.last_login = now()
        serializer.user.save()

        if settings.USERNAME_CHANGED_EMAIL_CONFIRMATION:
            context = {"user": serializer.user}
            to = [get_user_email(serializer.user)]
            settings.EMAIL.username_changed_confirmation(self.request, context).send(to)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # @extend_schema(tags=["auth", "User Management"])
    @action(["get"], detail=False, authentication_classes=[JWTAuthentication])
    def logout(self, request, *args, **kwargs):
        if settings.TOKEN_MODEL:
            settings.TOKEN_MODEL.objects.filter(user=request.user).delete()
            user_logged_out.send(
                sender=request.user.__class__,
                request=request,
                user=request.user,
            )
        if settings.CREATE_SESSION_ON_LOGIN:
            logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # @extend_schema(
    #     tags=["auth", "User Management"],
    #     # request=UserSerializer.PhoneMetadata,  # noqa: ERA001
    #     responses={status.HTTP_204_NO_CONTENT: None},
    # )
    @action(["POST"], detail=False, authentication_classes=[JWTAuthentication])
    def metadatas(self, request: Request, *args, **kwargs):
        serializer = UserSerializer.PhoneMetadata(
            data=request.data,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        serializer.update(request.user, serializer.validated_data)
        return Response(status=status.HTTP_204_NO_CONTENT)
