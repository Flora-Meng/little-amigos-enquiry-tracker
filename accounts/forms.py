from django import forms
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={"autocomplete": "email", "autofocus": True, "placeholder": "you@example.com"}
        ),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )


class StaffPasswordSetupForm(SetPasswordForm):
    """Finish onboarding when a location employee chooses a password."""

    def save(self, commit=True):
        user = super().save(commit=False)
        user.password_reset_required = False
        if commit:
            user.save(update_fields=("password", "password_reset_required", "updated_at"))
        return user
