from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django.contrib.auth import forms as admin_forms
from django.db import transaction
from django.forms import CharField
from django.forms import ChoiceField
from django.forms import EmailField
from django.forms import EmailInput
from django.forms import FileInput
from django.forms import ModelForm
from django.forms import NumberInput
from django.forms import Select
from django.forms import Textarea
from django.forms import TextInput
from django.forms import URLInput
from django.utils.translation import gettext_lazy as _

from core.helper.enums import UserRoleChoice

from .models import AgentProfile
from .models import SocialMediaLinks
from .models import User
from .models import UserProfile


class UserAdminChangeForm(admin_forms.UserChangeForm):
    """Form for updating users in the Django Admin."""

    class Meta(admin_forms.UserChangeForm.Meta):  # type: ignore[name-defined]
        model = User
        field_classes = {"email": EmailField}


class UserAdminCreationForm(admin_forms.UserCreationForm):
    """
    Form for User Creation in the Admin Area.
    To change user signup, see UserSignupForm and UserSocialSignupForm.
    """

    class Meta(admin_forms.UserCreationForm.Meta):  # type: ignore[name-defined]
        model = User
        fields = ("email",)
        field_classes = {"email": EmailField}
        error_messages = {
            "email": {"unique": _("This email has already been taken.")},
        }


class UserSignupForm(SignupForm):
    """
    Custom signup form for regular users (default role: USER)
    Form that will be rendered on a user sign up section/screen.
    Default fields will be added automatically.
    Check UserSocialSignupForm for accounts created from social.
    """

    name = CharField(max_length=255, label=_("Full Name"))
    role = ChoiceField(
        choices=UserRoleChoice.choices,
        label=_("Role"),
        initial=UserRoleChoice.CUSTOMER,
        widget=Select(
            attrs={
                "placeholder": "Choose type of user you want to sign up as",
                "class": "form-control form-select user-choices",
            },
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget = EmailInput(
            attrs={
                "placeholder": "Enter your email",
                "class": "form-control",
            },
        )
        self.fields["name"].widget = TextInput(
            attrs={
                "placeholder": "Full Name",
                "class": "form-control",
            },
        )

    # def save(self, request):
    #     """
    #     Creates the user and assigns the appropriate role & profile.
    #     """
    #     user = super().save(request)

    #     # Assign the role and name from the form to the user object
    #     user.role = self.cleaned_data.get("role")
    #     user.name = self.cleaned_data.get("name")

    #     # Save the user object again to persist the role
    #     user.save(update_fields=["name", "role"])  # Update only the role field

    #     if user.role == UserRoleChoice.CUSTOMER.value:
    #         UserProfile.objects.create(user=user)
    #     elif user.role == UserRoleChoice.AGENT.value:
    #         AgentProfile.objects.create(user=user)
    #     elif user.role == UserRoleChoice.REAL_ESTATE_OWNER.value:
    #         RealEstateOwnerProfile.objects.create(user=user)

    #     return user

    def save(self, request):
        """
        Creates the user and assigns the appropriate role & profile.
        """
        with transaction.atomic():
            user = super().save(request)
            user.role = self.cleaned_data["role"]
            user.name = self.cleaned_data["name"]
            user.save(update_fields=["name", "role"])

            profile_classes = {
                UserRoleChoice.CUSTOMER: UserProfile,
                UserRoleChoice.AGENT: AgentProfile,
                # UserRoleChoice.REAL_ESTATE_OWNER: RealEstateOwnerProfile,
            }

            profile_class = profile_classes.get(user.role)
            if profile_class:
                profile_class.objects.create(user=user)

        return user


class UserSocialSignupForm(SocialSignupForm):
    """
    Renders the form when user has signed up using social accounts.
    Default fields will be added automatically.
    See UserSignupForm otherwise.
    """


#  Profile Forms setup


class SocialMediaLinksForm(ModelForm):
    """
    Form to handle social media
    """

    class Meta:
        model = SocialMediaLinks
        fields = ["facebook", "twitter", "linkedin"]
        widgets = {
            "facebook": URLInput(
                attrs={
                    "placeholder": "Facebook URL",
                    "class": "form-control",
                },
            ),
            "twitter": URLInput(
                attrs={
                    "placeholder": "Twitter URL",
                    "class": "form-control",
                },
            ),
            "linkedin": URLInput(
                attrs={
                    "placeholder": "LinkedIn URL",
                    "class": "form-control",
                },
            ),
        }


class AgentProfileForm(ModelForm):
    """
    Form to handle agent profile
    """

    class Meta:
        model = AgentProfile
        fields = [
            "office_phone_no",
            "office_location",
            "description",
            "office_address",
            "profile_picture",
            "company_name",
            "license_number",
            "agent_type",
            "company_registration_number",
            "company_registration_document",
            "license_document",
        ]
        widgets = {
            "company_name": TextInput(
                attrs={
                    "placeholder": "Company Name",
                    "class": "form-control",
                },
            ),
            "office_phone_no": TextInput(
                attrs={
                    "placeholder": "Phone Number",
                    "class": "form-control",
                },
            ),
            "office_location": TextInput(
                attrs={
                    "placeholder": "Office Location",
                    "class": "form-control",
                },
            ),
            "office_phone_no": TextInput(
                attrs={
                    "placeholder": "Office Phone Number",
                    "class": "form-control",
                },
            ),
            "office_address": TextInput(
                attrs={
                    "placeholder": "Office Address",
                    "class": "form-control",
                },
            ),
            "profile_picture": FileInput(
                attrs={
                    "class": "form-control",
                },
            ),
            "company_registration_document": FileInput(
                attrs={
                    "class": "form-control",
                },
            ),
            "license_document": FileInput(
                attrs={
                    "class": "form-control",
                },
            ),
            "company_registration_number": TextInput(
                attrs={
                    "placeholder": "Company Registration Number",
                    "class": "form-control",
                },
            ),
            "description": TextInput(
                attrs={
                    "placeholder": "Describe yourself",
                    "class": "form-control",
                },
            ),
            "license_number": TextInput(
                attrs={
                    "placeholder": "License Number",
                    "class": "form-control",
                },
            ),
            "agent_type": Select(
                attrs={
                    "class": "dropdown-item",
                },
            ),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user:
            try:
                agent_profile = user.agent_profile
                if agent_profile.agent_type:
                    self.fields["agent_type"].disabled = True
                    self.fields[
                        "agent_type"
                    ].required = False  # ensure no validation error
            except AgentProfile.DoesNotExist:
                pass


class UsersProfileForm(ModelForm):
    """
    Form to handle user profile updates.
    Accepts 'user' for potential future customization.
    """

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Example: if you want to conditionally disable fields later based on the user
        if user:
            self.user = user  # Save user to the form instance for future use

    class Meta:
        model = UserProfile
        fields = [
            "phone_number",
            "address",
            "profile_picture",
            "preferred_location",
            "preferred_property_type",
            "min_budget",
            "max_budget",
            "preferred_features",
            "is_premium",
        ]
        widgets = {
            "phone_number": TextInput(
                attrs={
                    "placeholder": "Phone Number",
                    "class": "form-control",
                },
            ),
            "address": Textarea(
                attrs={
                    "placeholder": "Address",
                    "class": "form-control",
                    "rows": 2,
                },
            ),
            "profile_picture": FileInput(
                attrs={
                    "class": "form-control",
                },
            ),
            "preferred_location": TextInput(
                attrs={
                    "placeholder": "Preferred Location",
                    "class": "form-control",
                },
            ),
            "preferred_property_type": TextInput(
                attrs={
                    "placeholder": "Preferred Property Type",
                    "class": "form-control",
                },
            ),
            "min_budget": NumberInput(
                attrs={
                    "placeholder": "Min Budget",
                    "class": "form-control",
                },
            ),
            "max_budget": NumberInput(
                attrs={
                    "placeholder": "Max Budget",
                    "class": "form-control",
                },
            ),
            "preferred_features": Textarea(
                attrs={
                    "placeholder": "Preferred Features (comma-separated or JSON)",
                    "class": "form-control",
                    "rows": 3,
                },
            ),
        }


# class RealEstateOwnerProfileForm(ModelForm):
#     """
#     Form to handle real estate owner profile
#     """
#     model = RealEstateOwnerProfile
#     fields = ["phone_number", "address", "profile_picture"]
#     widgets = {
#         "phone_number": TextInput(attrs={
#             "placeholder": "Phone Number",
#             "class": "form-control"
#         }),
#         "address": TextInput(attrs={
#             "placeholder": "Address",
#             "class": "form-control"
#         }),
#         "profile_picture": FileInput(attrs={
#             "class": "form-control"
#         }),
#     }


class SuperCustomUserCreationForm(UserAdminCreationForm):
    """
    Custom form for creating a superuser.
    Inherits from UserAdminCreationForm and adds necessary fields/validations.
    """

    class Meta(UserAdminCreationForm.Meta):
        model = User
        fields = ("email", "password1", "password2")
        field_classes = {"email": EmailField}

    def save(self, commit=True):
        user = super().save(commit=False)
        # Set superuser and staff flags
        user.is_staff = True
        user.is_superuser = True
        if commit:
            user.save()
        return user
