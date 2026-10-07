from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(
        choices=User.Role.choices,
        label="I am a",
        initial=User.Role.TENANT,
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "phone_number", "role")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists. "
                "If you never verified it, use the Verify email page to get a new code."
            )
        return email

    def clean(self):
        cleaned = super().clean()
        # Landlords must be reachable by tenants.
        if cleaned.get("role") == User.Role.LANDLORD and not cleaned.get("phone_number"):
            self.add_error("phone_number", "Landlords must provide a phone number.")
        return cleaned


class LoginForm(AuthenticationForm):
    """Gives a clear message to people who registered but never verified their email."""

    def clean(self):
        try:
            return super().clean()
        except forms.ValidationError:
            username = self.data.get("username", "")
            password = self.data.get("password", "")
            user = User.objects.filter(username__iexact=username).first() if username else None
            if user and not user.is_active and user.check_password(password):
                raise forms.ValidationError(
                    "Your email is not verified yet. Use the Verify email link below "
                    "to enter the code we sent you.",
                    code="unverified",
                )
            raise


class VerifyEmailForm(forms.Form):
    email = forms.EmailField(label="Email")
    code = forms.CharField(
        label="6-digit code",
        min_length=6,
        max_length=6,
        widget=forms.TextInput(
            attrs={
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
                "placeholder": "123456",
            }
        ),
    )

    def clean_code(self):
        code = self.cleaned_data["code"].strip()
        if not code.isdigit():
            raise forms.ValidationError("The code is 6 digits.")
        return code