import uuid
import hashlib
import secrets

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from accounts.models import Location


class Enquiry(models.Model):
    class Source(models.TextChoices):
        ONLINE = "online", "Online"
        STORE = "store", "Store"

    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        WAITING_FOR_REPLY = "waiting_for_reply", "Waiting for reply"
        FOLLOW_UP = "follow_up", "Follow-up"
        BOOKED = "booked", "Booked"
        CLOSED = "closed", "Closed"

    class ClosedReason(models.TextChoices):
        UNABLE_TO_CONTACT = "unable_to_contact", "Unable to contact"
        NO_LONGER_INTERESTED = "customer_no_longer_interested", "Customer no longer interested"
        PRICE = "price", "Price"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    postcode = models.CharField(max_length=12, blank=True)
    party_date = models.DateField(null=True, blank=True)
    party_date_unknown = models.BooleanField(default=False)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    normalised_email = models.CharField(max_length=254, blank=True, db_index=True)
    normalised_phone = models.CharField(max_length=40, blank=True, db_index=True)
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="enquiries")
    source = models.CharField(max_length=10, choices=Source.choices)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.NEW)
    booking_amount_aud = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    closed_reason = models.CharField(max_length=40, choices=ClosedReason.choices, blank=True)
    closed_reason_details = models.TextField(blank=True)
    follow_up_due_date = models.DateField(null=True, blank=True)
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="submitted_enquiries")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)
    zumo_conversation_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    original_zumo_message = models.TextField(blank=True)

    class Meta:
        db_table = "enquiries"
        indexes = [
            models.Index(fields=("location", "source", "status")),
            models.Index(fields=("follow_up_due_date",)),
            models.Index(fields=("created_at",)),
            models.Index(fields=("updated_at",)),
            models.Index(fields=("archived",)),
            models.Index(fields=("party_date",)),
        ]

    def clean(self):
        errors = {}
        if not self.email.strip() and not self.phone.strip():
            errors["email"] = "Provide at least an email address or phone number."
        if self.party_date and self.party_date_unknown:
            errors["party_date"] = "Choose a date or Not sure yet, not both."
        if self.status == self.Status.BOOKED and self.booking_amount_aud is None:
            errors["booking_amount_aud"] = "A booking amount is required when booked."
        if self.status == self.Status.CLOSED and not self.closed_reason:
            errors["closed_reason"] = "A closed reason is required when closed."
        if self.closed_reason == self.ClosedReason.OTHER and not self.closed_reason_details.strip():
            errors["closed_reason_details"] = "Provide details when the reason is Other."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        from .services import normalise_email, normalise_phone

        self.normalised_email = normalise_email(self.email)
        self.normalised_phone = normalise_phone(self.phone)
        super().save(*args, **kwargs)


class Note(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enquiry = models.ForeignKey(Enquiry, on_delete=models.PROTECT, related_name="notes")
    body = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="notes")
    author_display_name = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notes"
        ordering = ("created_at",)

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Notes are append-only and cannot be edited.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Notes are append-only and cannot be deleted.")


class ZumoImportDecision(models.Model):
    class Decision(models.TextChoices):
        IMPORTED = "imported", "Imported"
        IGNORED = "ignored", "Ignored"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    zumo_conversation_id = models.CharField(max_length=255, unique=True)
    zumo_conversation_url = models.URLField(max_length=1000)
    decision = models.CharField(max_length=10, choices=Decision.choices)
    linked_enquiry = models.ForeignKey(Enquiry, null=True, blank=True, on_delete=models.PROTECT, related_name="zumo_decisions")
    detected_postcode = models.CharField(max_length=12, blank=True)
    detected_location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.PROTECT, related_name="zumo_decisions")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="zumo_reviews")
    reviewed_at = models.DateTimeField(auto_now_add=True)
    original_message_snapshot = models.TextField(blank=True)
    possible_duplicate = models.BooleanField(default=False)

    class Meta:
        db_table = "zumo_import_decisions"


class ExtensionToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, default="Chrome extension")
    token_prefix = models.CharField(max_length=12)
    token_hash = models.CharField(max_length=64, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="extension_tokens",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "extension_tokens"
        ordering = ("-created_at",)

    @staticmethod
    def hash_token(raw_token):
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    @classmethod
    def issue(cls, *, user, name="Chrome extension"):
        raw_token = f"laet_{secrets.token_urlsafe(32)}"
        token = cls.objects.create(
            name=name,
            token_prefix=raw_token[:12],
            token_hash=cls.hash_token(raw_token),
            user=user,
        )
        return token, raw_token

    @classmethod
    def authenticate(cls, raw_token):
        if not raw_token:
            return None
        token = cls.objects.select_related("user").filter(
            token_hash=cls.hash_token(raw_token),
            revoked_at__isnull=True,
            user__is_active=True,
            user__role="admin",
        ).first()
        if token:
            token.last_used_at = timezone.now()
            token.save(update_fields=("last_used_at",))
        return token
