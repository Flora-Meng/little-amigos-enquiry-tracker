from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.db.models import OuterRef, Subquery
from django.shortcuts import render
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from enquiries.models import Enquiry, Note
from enquiries.services import due_today, overdue

from .authorization import enquiries_visible_to
from .models import User


@login_required
def dashboard(request):
    latest_note = Note.objects.filter(enquiry_id=OuterRef("pk")).order_by("-created_at")
    visible = enquiries_visible_to(
        request.user,
        Enquiry.objects.filter(archived=False)
        .select_related("location")
        .annotate(
            latest_note_body=Subquery(latest_note.values("body")[:1]),
            latest_note_author_name=Subquery(
                latest_note.values("author_display_name")[:1]
            ),
        ),
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
            {
                "cards": cards,
                "booked_total": booked_total,
                "recent": recent,
                "status_choices": Enquiry.Status.choices,
            },
        )

    cards = (
        ("New store enquiries", visible.filter(status=Enquiry.Status.NEW).count()),
        ("Current open enquiries", visible.exclude(status__in=(Enquiry.Status.BOOKED, Enquiry.Status.CLOSED)).count()),
        ("Booked enquiries", visible.filter(status=Enquiry.Status.BOOKED).count()),
    )
    return render(
        request,
        "accounts/staff_dashboard.html",
        {"cards": cards, "recent": recent, "status_choices": Enquiry.Status.choices},
    )


@login_required
def team_accounts(request):
    """Let an administrator securely onboard the fixed location accounts."""
    if request.user.role != User.Role.ADMIN:
        raise PermissionDenied("Only administrators can manage team accounts.")

    accounts = []
    users = User.objects.filter(role=User.Role.STAFF).select_related("location").order_by("location__name")
    for user in users:
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        setup_path = reverse("staff_password_setup", kwargs={"uidb64": uid, "token": token})
        accounts.append(
            {
                "user": user,
                "setup_url": request.build_absolute_uri(setup_path),
                "password_ready": user.has_usable_password(),
            }
        )

    return render(request, "accounts/team_accounts.html", {"accounts": accounts})


@login_required
def package_showcase(request):
    """Read-only, location-scoped package presentation for pre-booking conversations."""
    from party_summaries.forms import EXTRA_MENU_OPTIONS

    if request.user.role == User.Role.STAFF and (
        not request.user.location or request.user.location.code != "canberra"
    ):
        raise Http404
    if request.user.role not in {User.Role.ADMIN, User.Role.STAFF}:
        raise Http404

    packages = (
        {
            "key": "single",
            "label": "Single room",
            "price": 799,
            "price_label": "Weekday $799 · Weekend $999",
            "menu": "single",
            "voucher": 0,
            "photos": (
                "package_showcase/canberra/single-1.jpg",
                "package_showcase/canberra/single-2.jpg",
            ),
        },
        {
            "key": "double-1280",
            "label": "Double (food voucher) · Weekday",
            "price": 1280,
            "price_label": "$1,280",
            "menu": "voucher",
            "voucher": 180,
            "photos": (
                "package_showcase/canberra/double-room-1-20261009.jpg",
                "package_showcase/canberra/double-2.jpg",
            ),
        },
        {
            "key": "double-1580",
            "label": "Double (food voucher) · Weekend",
            "price": 1580,
            "price_label": "$1,580",
            "menu": "voucher",
            "voucher": 180,
            "photos": (
                "package_showcase/canberra/double-room-1-20261009.jpg",
                "package_showcase/canberra/double-2.jpg",
            ),
        },
        {
            "key": "private-2h",
            "label": "Private · 2 hours",
            "price": 1899,
            "price_label": "Weekday $1,899 · Weekend $2,199",
            "menu": "voucher",
            "voucher": 400,
            "photos": (
                "package_showcase/canberra/private-1.jpg",
                "package_showcase/canberra/private-2.jpg",
            ),
        },
        {
            "key": "private-3h",
            "label": "Private · 3 hours",
            "price": 2399,
            "price_label": "Weekday $2,399 · Weekend $2,699",
            "menu": "voucher",
            "voucher": 400,
            "photos": (
                "package_showcase/canberra/private-1.jpg",
                "package_showcase/canberra/private-2.jpg",
            ),
        },
    )
    voucher_groups = (
        ("Platters to share", EXTRA_MENU_OPTIONS[0:23]),
        ("Salad and pasta bowls", EXTRA_MENU_OPTIONS[23:30]),
        ("Pizzas", EXTRA_MENU_OPTIONS[30:34]),
        ("Fryer trays", EXTRA_MENU_OPTIONS[34:40]),
        ("Toasts and wraps", EXTRA_MENU_OPTIONS[40:45]),
    )
    return render(
        request,
        "package_showcase/canberra.html",
        {"packages": packages, "voucher_groups": voucher_groups},
    )
