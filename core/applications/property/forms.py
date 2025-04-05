from django import forms
from django.views.generic import CreateView, UpdateView, DetailView, ListView, DeleteView
from django.urls import reverse_lazy

from core.applications.property.models import Amenity, Lead, Property, PropertyImage, PropertyType


# Forms

class PropertyForm(forms.ModelForm):
    amenities = forms.ModelMultipleChoiceField(
        queryset=Amenity.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={"class": "mb-10"}),
        required=False,  # Allow properties without amenities
        label="Select Amenities",
    )
    property_type = forms.ModelChoiceField(
        queryset=PropertyType.objects.all(),
        widget=forms.Select(attrs={
            "class": "mb-10","id": "property_type_select"
        }),
        label="Property Type",
    )
    new_property_type = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "mb-10", "id": "new_property_type_input", 
            "placeholder": "Enter new property type"
        }),
        label="New Property Type (optional)"
    )
    class Meta:
        model = Property
        fields = [
            "title", "description", "property_type", 
            "price", "location", "bedrooms", "bathrooms", 
            "sqft", "is_available", "amenities", 
            "new_property_type"
        ]
        widgets = {
            "title": forms.TextInput(attrs={
                "placeholder": "Enter property title",
                "class": "mb-10",
            }),
            "description": forms.Textarea(attrs={
                "placeholder": "Enter property description",
                "class": "mb-10",
                "rows": 4,
            }),
            # "property_type": forms.Select(attrs={
                  
            # }),
            "price": forms.NumberInput(attrs={
                "placeholder": "Enter price",
                "class": "mb-10",
                "min": "0",
                "step": "0.01",  
            }),
            "location": forms.TextInput(attrs={
                "placeholder": "Enter location",
                "class": "mb-10",
            }),
            "bedrooms": forms.NumberInput(attrs={
                "class": "mb-10",
                "min": "0",
                "step": "1",
            }),
            "bathrooms": forms.NumberInput(attrs={
                "class": "mb-10",
                "min": "0",
                "step": "1",
            }),
            "sqft": forms.NumberInput(attrs={
                "placeholder": "Enter size in sqft",
                "class": "mb-10",
                "min": "0",
                "step": "1",
            }),
            "is_available": forms.CheckboxInput(attrs={
                "class": "mb-10",
            }),
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

    def clean(self):
        cleaned_data = super().clean()
        property_type = cleaned_data.get("property_type")
        new_property_type = cleaned_data.get("new_property_type", "").strip()

        # If both fields are empty
        if not property_type and not new_property_type:
            raise forms.ValidationError(
                "Please select a property type or enter a new one.",
                code='missing_property_type'
            )

        # If new property type is entered
        if new_property_type:
            # Validate the new type
            if len(new_property_type) < 3:
                raise forms.ValidationError(
                    "Property type must be at least 3 characters.",
                    code='invalid_property_type_length'
                )

            # Check for existing type (case insensitive)
            existing_type = PropertyType.objects.filter(
                title__iexact=new_property_type
            ).first()

            if existing_type:
                # Use existing type instead
                cleaned_data["property_type"] = existing_type
                self.instance.property_type = existing_type  # Assign to model instance
            else:
                # Create and assign new type
                new_type = PropertyType.objects.create(title=new_property_type)
                cleaned_data["property_type"] = new_type
                self.instance.property_type = new_type  # Assign to model instance

            # Clear the temporary new_property_type field
            cleaned_data["new_property_type"] = ""
            if hasattr(self.instance, 'new_property_type'):
                self.instance.new_property_type = ""

        return cleaned_data

    def save(self, commit=True):
        # Ensure property_type is properly set before saving
        instance = super().save(commit=False)
        if not instance.property_type and hasattr(self, 'cleaned_data'):
            instance.property_type = self.cleaned_data.get('property_type')
        
        if commit:
            instance.save()
            self.save_m2m()  # Don't forget this for ManyToMany fields
            
        return instance
    

class PropertyImageForm(forms.ModelForm):
    image = forms.FileField(widget = forms.TextInput(attrs={
            "name": "images",
            "type": "File",
            "class": "form-control",
            "multiple": "True",
        }), label = "")
    class Meta:
        model = PropertyImage
        fields = ["property", "image"]


class LeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = ["agent", "user", "property", "message", "status"]


# class ChatMessageForm(forms.ModelForm):
#     class Meta:
#         model = ChatMessage
#         fields = ["sender", "receiver", "message"]


# class RentalApplicationForm(forms.ModelForm):
#     class Meta:
#         model = RentalApplication
#         fields = ["user", "property", "agent", "status"]


# class PaymentForm(forms.ModelForm):
#     class Meta:
#         model = Payment
#         fields = ["user", "property", "amount", "payment_method", "payment_status", "transaction_id"]


# class NotificationForm(forms.ModelForm):
#     class Meta:
#         model = Notification
#         fields = ["recipient", "message", "is_read"]


# Views

