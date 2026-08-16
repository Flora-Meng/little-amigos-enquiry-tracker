from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from enquiries.models import Enquiry
from enquiries.services import due_today, overdue

from .authorization import enquiries_visible_to
from .models import User


@login_required
def dashboard(request):
    visible = enquiries_visible_to(
        request.user,
        Enquiry.objects.filter(archived=False).select_related("location"),
    )
    recent = visible.order_by("-updated_at")[:8]

    if request.user.role == User.Role.ADMIN:
        cards = (
            ("New store enquiries", visible.filter(source=Enquiry.Source.STORE, status=Enquiry.Status.NEW).count(), "new-store"),
            ("Waiting for reply", visible.filter(status=Enquiry.Status.WAITING_FOR_REPLY).count(), "waiting"),
            ("Follow-ups due today", due_today(visible).count(), "due"),
            ("Overdue follow-ups", overdue(visible).count(), "overdue"),
            ("Booked", visible.filter(status=Enquiry.Status.BOOKED).count(), "booked"),
        )
        booked_total = sum(
            visible.filter(status=Enquiry.Status.BOOKED).values_list("booking_amount_aud", flat=True)
        )
        return render(
            request,
            "accounts/admin_dashboard.html",
            {"cards": cards, "booked_total": booked_total, "recent": recent},
        )

    cards = (
        ("New store enquiries", visible.filter(status=Enquiry.Status.NEW).count()),
        ("Current open enquiries", visible.exclude(status__in=(Enquiry.Status.BOOKED, Enquiry.Status.CLOSED)).count()),
        ("Booked enquiries", visible.filter(status=Enquiry.Status.BOOKED).count()),
    )
    return render(
        request,
        "accounts/staff_dashboard.html",
        {"cards": cards, "recent": recent},
    )
