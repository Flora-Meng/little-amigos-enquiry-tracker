from django import forms

from accounts.models import Location, User

from .models import Enquiry


class StoreEnquiryForm(forms.ModelForm):
    initial_note = forms.CharField(
        label="Initial note",
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": "Add useful context from the conversation…",
            }
        ),
    )

    class Meta:
        model = Enquiry
        fields = (
            "name",
            "phone",
            "email",
            "postcode",
            "party_date",
            "party_date_unknown",
            "location",
            "source",
        )
        labels = {
            "party_date_unknown": "Not sure yet",
            "source": "Source",
        }
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "name"}),
            "phone": forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "postcode": forms.TextInput(attrs={"autocomplete": "postal-code", "inputmode": "numeric"}),
            "party_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["location"].queryset = Location.objects.order_by("name")
        self.fields["location"].empty_label = "Select a location"
        if user.role == User.Role.STAFF:
            self.fields.pop("location")
            self.fields.pop("source")
        else:
            self.fields["location"].required = True
            self.fields["source"].required = False
            self.fields["source"].choices = Enquiry.Source.choices
            self.fields["source"].initial = Enquiry.Source.STORE

    def clean(self):
        cleaned = super().clean()
        email = (cleaned.get("email") or "").strip()
        phone = (cleaned.get("phone") or "").strip()
        party_date = cleaned.get("party_date")
        unknown = cleaned.get("party_date_unknown")
        if self.user.role == User.Role.ADMIN:
            cleaned["source"] = cleaned.get("source") or Enquiry.Source.STORE

        if not email and not phone:
            message = "Provide at least a phone number or email address."
            self.add_error("phone", message)
            self.add_error("email", message)
        if party_date and unknown:
            self.add_error("party_date", "Choose a date or Not sure yet, not both.")
        return cleaned


class QuickStatusForm(forms.Form):
    status = forms.ChoiceField(choices=Enquiry.Status.choices)


class EnquiryFilterForm(forms.Form):
    search = forms.CharField(
        required=False,
        label="Search",
        widget=forms.SearchInput(attrs={"placeholder": "Name, phone or email"}),
    )
    location = forms.ModelChoiceField(
        required=False,
        queryset=Location.objects.none(),
        empty_label="All locations",
    )
    source = forms.ChoiceField(
        required=False,
        choices=[("", "All sources"), *Enquiry.Source.choices],
    )
    status = forms.ChoiceField(
        required=False,
        choices=[("", "All statuses"), *Enquiry.Status.choices],
    )
    party_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    created_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    follow_up = forms.ChoiceField(
        required=False,
        choices=(
            ("", "Any follow-up"),
            ("due_today", "Due today"),
            ("overdue", "Overdue"),
        ),
    )
    archived = forms.ChoiceField(
        required=False,
        choices=(
            ("", "Active only"),
            ("only", "Archived only"),
            ("all", "Active and archived"),
        ),
    )
    sort = forms.ChoiceField(
        required=False,
        choices=(
            ("newest", "Newest submitted"),
            ("updated", "Most recently updated"),
            ("party_date", "Nearest party date"),
        ),
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["location"].queryset = Location.objects.order_by("name")
        if user.role == User.Role.STAFF:
            self.fields.pop("location")
            self.fields.pop("source")


class EnquiryAdminUpdateForm(forms.ModelForm):
    class Meta:
        model = Enquiry
        fields = (
            "name", "phone", "email", "postcode", "party_date",
            "party_date_unknown", "location", "status", "follow_up_due_date",
            "booking_amount_aud", "closed_reason", "closed_reason_details",
        )
        labels = {
            "party_date_unknown": "Not sure yet",
            "booking_amount_aud": "Booking amount (AUD)",
            "closed_reason_details": "Closed reason details",
        }
        widgets = {
            "party_date": forms.DateInput(attrs={"type": "date"}),
            "follow_up_due_date": forms.DateInput(attrs={"type": "date"}),
            "closed_reason_details": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        reason = cleaned.get("closed_reason")
        details = (cleaned.get("closed_reason_details") or "").strip()
        if status == Enquiry.Status.BOOKED and cleaned.get("booking_amount_aud") is None:
            self.add_error("booking_amount_aud", "Enter the booking amount in AUD.")
        if status == Enquiry.Status.CLOSED and reason == Enquiry.ClosedReason.OTHER and not details:
            self.add_error("closed_reason_details", "Explain the reason when Other is selected.")
        return cleaned


class NoteForm(forms.Form):
    body = forms.CharField(
        label="Add a note",
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Write a new note…"}),
    )
