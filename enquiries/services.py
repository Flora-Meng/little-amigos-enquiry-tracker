from datetime import timedelta

from django.db.models import QuerySet
from django.utils import timezone

from .models import Enquiry


TERMINAL_STATUSES = (Enquiry.Status.BOOKED, Enquiry.Status.CLOSED)
REMINDER_STATUSES = (Enquiry.Status.WAITING_FOR_REPLY, Enquiry.Status.FOLLOW_UP)


def normalise_email(value):
    return (value or "").strip().lower()


def normalise_phone(value):
    digits = "".join(character for character in (value or "") if character.isdigit())
    if digits.startswith("0061"):
        digits = digits[2:]
    if digits.startswith("61") and len(digits) == 11:
        digits = "0" + digits[2:]
    return digits


def find_duplicates(queryset: QuerySet, *, email="", phone="") -> QuerySet:
    from django.db.models import Q

    email_value = normalise_email(email)
    phone_value = normalise_phone(phone)
    match = Q()
    if email_value:
        match |= Q(normalised_email=email_value)
    if phone_value:
        match |= Q(normalised_phone=phone_value)
    if not email_value and not phone_value:
        return queryset.none()
    return queryset.filter(match).distinct().order_by("-created_at")


def two_calendar_days_from(today=None):
    """Return the business reminder date using the configured local timezone."""
    return (today or timezone.localdate()) + timedelta(days=2)


def apply_status_rules(enquiry, previous_status, *, today=None):
    """Apply authoritative reminder and terminal-status rules before saving."""
    status_changed = enquiry.status != previous_status
    if status_changed and enquiry.status in REMINDER_STATUSES:
        enquiry.follow_up_due_date = two_calendar_days_from(today)
    elif enquiry.status in TERMINAL_STATUSES:
        enquiry.follow_up_due_date = None

    if enquiry.status != Enquiry.Status.BOOKED:
        enquiry.booking_amount_aud = None
    if enquiry.status != Enquiry.Status.CLOSED:
        enquiry.closed_reason = ""
        enquiry.closed_reason_details = ""
    return enquiry


def schedule_next_follow_up(enquiry, *, today=None):
    if enquiry.status in TERMINAL_STATUSES:
        raise ValueError("Booked or closed enquiries cannot have an active follow-up.")
    enquiry.follow_up_due_date = two_calendar_days_from(today)
    return enquiry


def active_follow_ups(queryset: QuerySet) -> QuerySet:
    return queryset.filter(archived=False).exclude(status__in=TERMINAL_STATUSES)


def due_today(queryset: QuerySet, *, today=None) -> QuerySet:
    return active_follow_ups(queryset).filter(
        follow_up_due_date=today or timezone.localdate()
    )


def overdue(queryset: QuerySet, *, today=None) -> QuerySet:
    return active_follow_ups(queryset).filter(
        follow_up_due_date__lt=today or timezone.localdate()
    )
