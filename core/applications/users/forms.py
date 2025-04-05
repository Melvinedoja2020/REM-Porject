from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django.contrib.auth import forms as admin_forms
from django.forms import (
    EmailField, EmailInput, FileInput, TextInput, CharField, ChoiceField, Select, URLInput
)
from django.utils.translation import gettext_lazy as _

from core.helper.enums import UserRoleChoice

from .models import AgentProfile, RealEstateOwnerProfile, SocialMediaLinks, User, UserProfile

from django.forms import ModelForm
from django.db import transaction


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
        widget=Select(attrs={
            "placeholder": "Choose type of user you want to sign up as",
            "class": "form-control form-select user-choices"
        })
    )


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget = EmailInput(
            attrs={
                "placeholder": "Enter your email", 
                "class": "form-control"
            }
        )
        self.fields["name"].widget = TextInput(
            attrs={
                "placeholder": "Full Name", 
                "class": "form-control"
            }
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
                UserRoleChoice.REAL_ESTATE_OWNER: RealEstateOwnerProfile,
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
            "facebook": URLInput(attrs={
                "placeholder": "Facebook URL",
                "class": "form-control"
            }),
            "twitter": URLInput(attrs={
                "placeholder": "Twitter URL",
                "class": "form-control"
            }),
            "linkedin": URLInput(attrs={
                "placeholder": "LinkedIn URL",
                "class": "form-control"
            }),
        }




class AgentProfileForm(ModelForm):
    """
    Form to handle agent profile
    """
    class Meta:
        model = AgentProfile
        fields = [
            "office_phone_no", "office_location", "description",
            "office_address", "profile_picture", "company_name"
        ]
        widgets = {
            "company_name": TextInput(attrs={
                "placeholder": "Company Name",
                "class": "form-control"
            }), 
            "office_phone_no": TextInput(attrs={
                "placeholder": "Phone Number",
                "class": "form-control"
            }),
            "office_location": TextInput(attrs={
                "placeholder": "Office Location",
                "class": "form-control"
            }),
            "office_phone_no": TextInput(attrs={
                "placeholder": "Office Phone Number",
                "class": "form-control"
            }),
            "office_address": TextInput(attrs={
                "placeholder": "Office Address",
                "class": "form-control"
            }),
            "profile_picture": FileInput(attrs={
                "class": "form-control"
            }),
            "description": TextInput(attrs={
                "placeholder": "Description",
                "class": "form-control"
            }),
        }



class UsersProfile(ModelForm):
    """ Form to handle Users Profile """
    class Meta:
        model = UserProfile
        fields = ["phone_number", "address", "profile_picture"]
        widgets = {
            "phone_number": TextInput(attrs={
                "placeholder": "Phone Number",
                "class": "form-control"
            }),
            "address": TextInput(attrs={
                "placeholder": "Address",
                "class": "form-control"
            }),
            "profile_picture": FileInput(attrs={
                "class": "form-control"
            })
        }


class RealEstateOwnerProfileForm(ModelForm):
    """
    Form to handle real estate owner profile
    """
    model = RealEstateOwnerProfile
    fields = ["phone_number", "address", "profile_picture"]
    widgets = {
        "phone_number": TextInput(attrs={
            "placeholder": "Phone Number",
            "class": "form-control"
        }),
        "address": TextInput(attrs={
            "placeholder": "Address",
            "class": "form-control"
        }),
        "profile_picture": FileInput(attrs={
            "class": "form-control"
        }),
    }