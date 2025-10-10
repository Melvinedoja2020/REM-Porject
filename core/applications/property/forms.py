from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from core.applications.property.models import Amenity
from core.applications.property.models import Lead
from core.applications.property.models import Property
from core.applications.property.models import PropertyImage
from core.applications.property.models import PropertySubscription
from core.applications.property.models import PropertyType
from core.applications.property.models import PropertyViewing
from core.applications.subscriptions.features import FEATURE_LIMITS
from core.applications.subscriptions.models import FeaturedListing
from core.helper.enums import PropertyTypeChoices, SubscriptionPlan


class PropertyForm(forms.ModelForm):
    amenities = forms.ModelMultipleChoiceField(
        queryset=Amenity.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={"class": "mb-10"}),
        required=False,  # Allow properties without amenities
        label="Select Amenities",
    )
    # property_type = forms.ModelChoiceField(
    #     queryset=PropertyType.objects.all(),
    #     widget=forms.Select(attrs={
    #         "class": "mb-10","id": "property_type_select"
    #     }),
    #     label="Property Type",
    # )
    property_type = forms.ChoiceField(
        choices=PropertyTypeChoices.choices,
        widget=forms.Select(
            attrs={
                "class": "mb-10",
                "id": "property_type_select",
            },
        ),
        label="Property Type",
    )
    new_property_type = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "mb-10",
                "id": "new_property_type_input",
                "placeholder": "Enter new property type",
            },
        ),
        label="New Property Type (optional)",
    )

    class Meta:
        model = Property
        fields = [
            "title",
            "description",
            "property_type",
            "price",
            "location",
            "bedrooms",
            "bathrooms",
            "sqft",
            "is_available",
            "amenities",
            "new_property_type",
            "cover_image",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "placeholder": "Enter property title",
                    "class": "mb-10",
                },
            ),
            "cover_image": forms.ClearableFileInput(
                attrs={
                    "class": "mb-10",
                    "accept": "image/*",
                },
            ),
            "description": forms.Textarea(
                attrs={
                    "placeholder": "Enter property description",
                    "class": "mb-10 form-control",
                    "rows": 4,
                },
            ),
            # "property_type": forms.Select(attrs={
            # }),
            "price": forms.NumberInput(
                attrs={
                    "placeholder": "Enter price",
                    "class": "mb-10",
                    "min": "0",
                    "step": "0.01",
                },
            ),
            "location": forms.TextInput(
                attrs={
                    "placeholder": "Enter location",
                    "class": "mb-10",
                },
            ),
            "bedrooms": forms.NumberInput(
                attrs={
                    "class": "mb-10",
                    "min": "0",
                    "step": "1",
                },
            ),
            "bathrooms": forms.NumberInput(
                attrs={
                    "class": "mb-10",
                    "min": "0",
                    "step": "1",
                },
            ),
            "sqft": forms.NumberInput(
                attrs={
                    "placeholder": "Enter size in sqft",
                    "class": "mb-10",
                    "min": "0",
                    "step": "1",
                },
            ),
            "is_available": forms.CheckboxInput(
                attrs={
                    "class": "mb-10",
                },
            ),
        }

    def clean_price(self):
        """Ensure price is not negative."""
        price = self.cleaned_data.get("price")
        if price is not None and price < 0:
            raise forms.ValidationError("Price cannot be negative.")
        return price

    def clean_sqft(self):
        """Ensure sqft is not negative."""
        sqft = self.cleaned_data.get("sqft")
        if sqft is not None and sqft < 0:
            raise forms.ValidationError("Square footage cannot be negative.")
        return sqft

    from django.core.exceptions import ValidationError

    def clean(self):
        cleaned_data = super().clean()
        property_type = cleaned_data.get("property_type")
        new_property_type = cleaned_data.get("new_property_type", "").strip()

        # ✅ Subscription-based property limit enforcement
        agent = getattr(self.instance, "agent", None)
        if agent:
            subscription = getattr(agent, "current_subscription", None)
            plan = subscription.plan if subscription else SubscriptionPlan.FREE
            property_count = agent.properties.count()
            limit = FEATURE_LIMITS.get(plan, {}).get("properties")

            if limit is not None and property_count >= limit:
                raise ValidationError(
                    {
                        "__all__": f"You have reached your property limit ({limit}) for the {plan} plan. Please upgrade your subscription."
                    }
                )

        # Existing property_type validation
        if not property_type and not new_property_type:
            raise ValidationError(
                "Please select a property type or enter a new one.",
                code="missing_property_type",
            )

        if new_property_type:
            if len(new_property_type) < 3:
                raise ValidationError(
                    "Property type must be at least 3 characters.",
                    code="invalid_property_type_length",
                )

            existing_type = PropertyType.objects.filter(
                title__iexact=new_property_type,
            ).first()

            if existing_type:
                cleaned_data["property_type"] = existing_type
                self.instance.property_type = existing_type
            else:
                new_type = PropertyType.objects.create(title=new_property_type)
                cleaned_data["property_type"] = new_type
                self.instance.property_type = new_type

            cleaned_data["new_property_type"] = ""
            if hasattr(self.instance, "new_property_type"):
                self.instance.new_property_type = ""

        return cleaned_data

    def save(self, commit=True):
        # Ensure property_type is properly set before saving
        instance = super().save(commit=False)
        if not instance.property_type and hasattr(self, "cleaned_data"):
            instance.property_type = self.cleaned_data.get("property_type")

        if commit:
            instance.save()
            self.save_m2m()  # Don"t forget this for ManyToMany fields

        return instance


class PropertyImageForm(forms.ModelForm):
    image = forms.FileField(
        widget=forms.TextInput(
            attrs={
                "name": "images",
                "type": "File",
                "class": "form-control",
                "multiple": "True",
            },
        ),
        label="",
    )

    class Meta:
        model = PropertyImage
        fields = ["property", "image"]


class FeaturedListingForm(forms.ModelForm):
    class Meta:
        model = FeaturedListing  # or whatever your model is called
        fields = ["property", "is_active", "boost_duration"]
        widgets = {
            "is_active": forms.CheckboxInput(attrs={"class": "mb-10"}),
            "boost_duration": forms.Select(attrs={"class": "mb-10"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        agent = getattr(self.instance, "agent", None)
        if agent:
            subscription = getattr(agent, "current_subscription", None)
            plan = subscription.plan if subscription else SubscriptionPlan.FREE
            active_boosts = agent.featured_properties.filter(is_active=True).count()
            limit = FEATURE_LIMITS.get(plan, {}).get("featured_listings")

            if limit is not None and active_boosts >= limit:
                raise forms.ValidationError(
                    f"You have reached your featured listing limit ({limit}) for the {plan} plan. "
                    f"Please upgrade your subscription."
                )

        return cleaned_data


class PropertySearchForm(forms.Form):
    q = forms.CharField(label="Search", required=False)
    location = forms.CharField(label="Location", required=False)
    # property_type = forms.ModelChoiceField(
    #     queryset=PropertyType.objects.all(), required=False, empty_label="Any Type"
    # )
    property_type = forms.ChoiceField(
        choices=[("", "Any")] + list(PropertyTypeChoices.choices),
        required=False,
        label="Listing Type",
    )
    min_price = forms.DecimalField(label="Min Price", required=False, min_value=0)
    max_price = forms.DecimalField(label="Max Price", required=False, min_value=0)
    min_bedrooms = forms.IntegerField(label="Min Bedrooms", required=False, min_value=0)
    min_bathrooms = forms.IntegerField(
        label="Min Bathrooms",
        required=False,
        min_value=0,
    )
    amenities = forms.ModelMultipleChoiceField(
        queryset=Amenity.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Amenities",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.update({"class": "form-select"})
            elif isinstance(field.widget, forms.CheckboxSelectMultiple):
                field.widget.attrs.update({"class": "form-check-input"})
            else:
                field.widget.attrs.update({"class": "form-control"})


class PropertySubscriptionForm(forms.ModelForm):
    class Meta:
        model = PropertySubscription
        fields = ["location", "property_type"]
        widgets = {
            "location": forms.TextInput(
                attrs={
                    "placeholder": "Enter location",
                    "class": "flex-grow",
                },
            ),
            "property_type": forms.Select(
                attrs={
                    "class": "flex-grow",
                },
            ),
        }


class LeadCreateForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = ["property_link", "message", "notes"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        property_queryset = kwargs.pop("property_queryset", None)
        super().__init__(*args, **kwargs)

        if property_queryset is not None:
            self.fields["property_link"].queryset = property_queryset

    def clean(self):
        cleaned_data = super().clean()
        property_link = cleaned_data.get("property_link")

        if self.user and property_link:
            if Lead.objects.filter(
                user=self.user,
                property_link=property_link,
            ).exists():
                raise ValidationError(
                    "You already have an existing lead for this property. "
                    "Please check your leads list or contact the agent.",
                )
        return cleaned_data


class LeadStatusForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = ["status", "notes"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(
                attrs={
                    "rows": 3,
                    "class": "form-control",
                    "placeholder": "Add private notes...",
                },
            ),
        }


class ViewingScheduleForm(forms.ModelForm):
    class Meta:
        model = PropertyViewing
        fields = ["scheduled_time"]
        widgets = {
            "scheduled_time": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "class": "form-control",
                    "min": timezone.now().strftime("%Y-%m-%dT%H:%M"),
                },
            ),
        }

    def clean_scheduled_time(self):
        scheduled_time = self.cleaned_data["scheduled_time"]
        if scheduled_time < timezone.now():
            raise ValidationError("Viewing time cannot be in the past")
        return scheduled_time
