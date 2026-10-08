from django import forms

from .models import House, HouseImage, Location


class HouseSearchForm(forms.Form):
    """Tenant search: location, rent range, bedrooms, bathrooms, property type."""

    location = forms.ModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        empty_label="Any location",
    )
    min_rent = forms.IntegerField(required=False, min_value=0)
    max_rent = forms.IntegerField(required=False, min_value=0)
    bedrooms = forms.IntegerField(required=False, min_value=0)
    bathrooms = forms.IntegerField(required=False, min_value=0)
    house_type = forms.ChoiceField(
        choices=[("", "Any type")] + list(House.HouseType.choices),
        required=False,
    )

    def clean(self):
        cleaned = super().clean()
        min_rent = cleaned.get("min_rent")
        max_rent = cleaned.get("max_rent")
        if min_rent is not None and max_rent is not None and min_rent > max_rent:
            raise forms.ValidationError("Min rent cannot be higher than max rent.")
        return cleaned


class HouseForm(forms.ModelForm):
    """Landlord add/edit house. The landlord is set in the view, not the form."""

    class Meta:
        model = House
        fields = [
            "title",
            "location",
            "rent",
            "bedrooms",
            "bathrooms",
            "house_type",
            "status",
            "description",
        ]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}


class HouseImageForm(forms.ModelForm):
    class Meta:
        model = HouseImage
        fields = ["image"]