from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import OuterRef, Prefetch, Subquery
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.views.decorators.http import require_POST
from enquiries.models import Enquiry, Note
from enquiries.services import due_today, overdue

from .authorization import enquiries_visible_to
from .models import (
    SouthlandShowcaseAddon,
    SouthlandShowcaseInvite,
    SouthlandShowcaseTheme,
    SouthlandShowcaseThemePhoto,
    User,
)


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
        return render(
            request,
            "accounts/admin_dashboard.html",
            {
                "cards": cards,
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
            "key": "double-voucher",
            "label": "Double (food voucher)",
            "price": 1099,
            "price_label": "Weekday $1,099 · Weekend $1,299",
            "menu": "voucher",
            "voucher": 180,
            "photos": (
                "package_showcase/canberra/double-room-1-20261009.jpg",
                "package_showcase/canberra/double-2.jpg",
            ),
        },
        {
            "key": "double",
            "label": "Double room",
            "price": 1280,
            "price_label": "Weekday $1,280 · Weekend $1,580",
            "menu": "double",
            "voucher": 0,
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


def southland_party_guide(request, token=None):
    """Public, read-only Southland theme and package guide."""
    invite = get_object_or_404(SouthlandShowcaseInvite, token=token) if token else None
    if invite and invite.estimated_guest_count:
        count = invite.estimated_guest_count
        invite.recommended_room = (
            "Single Room" if count <= 8 else
            "Double Room" if count <= 15 else
            "Triple Room" if count <= 25 else
            "Private Party"
        )
    packages = (
        {
            "key": "essential",
            "label": "Essential",
            "room": "Single room",
            "weekday": 699,
            "weekend": 899,
            "kids": 8,
            "adults": 10,
            "drinks": 1,
            "included": (
                "One fryer platter — choose mixed or vegetarian",
                "One seasonal fruit platter",
                "Two 10-inch pizzas — choose the flavours",
                "1 drink jar and 1 refillable water jar",
            ),
        },
        {
            "key": "signature",
            "label": "Signature",
            "room": "Double room",
            "weekday": 999,
            "weekend": 1299,
            "kids": 15,
            "adults": 20,
            "drinks": 2,
            "included": (
                "One fryer platter — choose mixed or vegetarian",
                "One seasonal fruit platter",
                "Four 10-inch pizzas — choose the flavours",
                "One salad bowl",
                "One mini burger platter — 10 pieces",
                "One toast platter — 12 pieces",
                "2 drink jars and 1 refillable water jar",
            ),
        },
        {
            "key": "ultimate",
            "label": "Ultimate",
            "room": "Triple room",
            "weekday": 1899,
            "weekend": 2199,
            "kids": 25,
            "adults": 30,
            "drinks": 6,
            "included": (
                "One fryer platter — choose mixed or vegetarian",
                "One seasonal fruit platter",
                "Four 10-inch pizzas — choose the flavours",
                "One salad bowl",
                "One mini burger platter — 10 pieces",
                "One taco platter — 12 pieces",
                "One pesto pasta bowl",
                "One toast platter — 12 pieces",
                "One sushi platter",
                "6 drink jars and 1 refillable water jar",
            ),
        },
        {
            "key": "private",
            "label": "Private",
            "room": "Whole venue hire",
            "weekday": 2699,
            "weekend": 2999,
            "kids": 35,
            "adults": 40,
            "drinks": 8,
            "included": (
                "One fryer platter — choose mixed or vegetarian",
                "One seasonal fruit platter",
                "Four 10-inch pizzas — choose the flavours",
                "One salad bowl",
                "One mini burger platter — 10 pieces",
                "One taco platter — 12 pieces",
                "One pesto pasta bowl",
                "One finger sandwich platter — 16 pieces",
                "One toast platter — 12 pieces",
                "One sushi platter",
                "8 drink jars and 1 refillable water jar",
            ),
        },
    )
    for package in packages:
        package["weekday_label"] = f"${package['weekday']:,}"
        package["weekend_label"] = f"${package['weekend']:,}"

    themes = list(
        SouthlandShowcaseTheme.objects.filter(is_active=True).prefetch_related(
            Prefetch("photos", queryset=SouthlandShowcaseThemePhoto.objects.order_by("sort_order", "id"))
        )
    )
    for theme in themes:
        theme.photo_urls = [_theme_photo_url(photo) for photo in theme.photos.all()]
        theme.cover_url = theme.photo_urls[0] if theme.photo_urls else ""
        theme.search_text = f"{theme.name} {theme.search_terms}".lower()

    addons = list(SouthlandShowcaseAddon.objects.filter(is_active=True))
    for addon in addons:
        addon.image_url = _addon_image_url(addon)
        addon.image_urls = _addon_image_urls(addon)
    return render(
        request,
        "package_showcase/southland_public.html",
        {"packages": packages, "themes": themes, "addons": addons, "invite": invite},
    )


def _theme_photo_url(photo):
    if photo.image_data:
        return reverse("southland_theme_photo", kwargs={"photo_id": photo.pk})
    return static(photo.static_path) if photo.static_path else ""


def _addon_image_url(addon):
    if addon.image_data:
        return reverse("southland_addon_image", kwargs={"addon_id": addon.pk})
    return static(addon.static_path) if addon.static_path else ""


def _addon_image_urls(addon):
    if addon.image_data:
        return [_addon_image_url(addon)]
    canberra_examples = {
        "Face painting": ("package_showcase/canberra/addons/face-painting.jpg",),
        "Customised cake": (
            "package_showcase/canberra/addons/cake-single-tier-guide.jpg",
            "package_showcase/canberra/addons/cake-double-tier-guide.jpg",
        ),
        "Entertainer or mascot": (
            "package_showcase/canberra/addons/entertainer-1.jpg",
            "package_showcase/canberra/addons/entertainer-2.jpg",
            "package_showcase/canberra/addons/mascot-1.jpg",
            "package_showcase/canberra/addons/mascot-2.jpg",
        ),
    }
    paths = canberra_examples.get(addon.name)
    if paths:
        return [static(path) for path in paths]
    return [_addon_image_url(addon)] if addon.static_path else []


def southland_theme_photo(request, photo_id):
    photo = get_object_or_404(SouthlandShowcaseThemePhoto, pk=photo_id, image_data__isnull=False)
    response = HttpResponse(bytes(photo.image_data), content_type=photo.image_content_type or "image/jpeg")
    response["Cache-Control"] = "public, max-age=86400"
    return response


def southland_addon_image(request, addon_id):
    addon = get_object_or_404(SouthlandShowcaseAddon, pk=addon_id, image_data__isnull=False)
    response = HttpResponse(bytes(addon.image_data), content_type=addon.image_content_type or "image/jpeg")
    response["Cache-Control"] = "public, max-age=86400"
    return response


def _require_admin(user):
    if user.role != User.Role.ADMIN:
        raise PermissionDenied("Only administrators can manage the Southland showcase.")


def _validated_image(upload):
    if not upload:
        return None
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if upload.content_type not in allowed:
        raise ValueError("Upload a JPG, PNG or WebP image.")
    if upload.size > 5 * 1024 * 1024:
        raise ValueError("Each image must be 5 MB or smaller.")
    return {
        "image_data": upload.read(),
        "image_name": upload.name[:255],
        "image_content_type": upload.content_type,
    }


@login_required
def southland_showcase_manage(request):
    _require_admin(request.user)
    themes = list(SouthlandShowcaseTheme.objects.prefetch_related("photos").all())
    for theme in themes:
        theme.admin_photos = list(theme.photos.all())
        for photo in theme.admin_photos:
            photo.preview_url = _theme_photo_url(photo)
    addons = list(SouthlandShowcaseAddon.objects.all())
    for addon in addons:
        addon.image_url = _addon_image_url(addon)
    return render(
        request,
        "accounts/southland_showcase_manage.html",
        {
            "themes": themes,
            "addons": addons,
            "category_choices": SouthlandShowcaseTheme.Category.choices,
        },
    )


@login_required
@require_POST
def southland_showcase_update(request):
    _require_admin(request.user)
    action = request.POST.get("action", "")
    try:
        with transaction.atomic():
            if action == "add_theme":
                name = request.POST.get("name", "").strip()
                if not name:
                    raise ValueError("Theme name is required.")
                category = request.POST.get("category", SouthlandShowcaseTheme.Category.FAVOURITES)
                if category not in SouthlandShowcaseTheme.Category.values:
                    raise ValueError("Choose a valid theme category.")
                theme = SouthlandShowcaseTheme.objects.create(
                    name=name,
                    category=category,
                    search_terms=request.POST.get("search_terms", "").strip(),
                    description=request.POST.get("description", "").strip(),
                    sort_order=(SouthlandShowcaseTheme.objects.order_by("-sort_order").values_list("sort_order", flat=True).first() or 0) + 1,
                )
                image = _validated_image(request.FILES.get("image"))
                if image:
                    SouthlandShowcaseThemePhoto.objects.create(theme=theme, **image)
                messages.success(request, f"{theme.name} was added.")
            elif action == "add_theme_photo":
                theme = get_object_or_404(SouthlandShowcaseTheme, pk=request.POST.get("theme_id"))
                image = _validated_image(request.FILES.get("image"))
                if not image:
                    raise ValueError("Choose an image to upload.")
                SouthlandShowcaseThemePhoto.objects.create(
                    theme=theme,
                    sort_order=theme.photos.count() + 1,
                    **image,
                )
                messages.success(request, f"A photo was added to {theme.name}.")
            elif action == "toggle_theme":
                theme = get_object_or_404(SouthlandShowcaseTheme, pk=request.POST.get("theme_id"))
                theme.is_active = not theme.is_active
                theme.save(update_fields=("is_active", "updated_at"))
                messages.success(request, f"{theme.name} is now {'visible' if theme.is_active else 'hidden'}.")
            elif action == "delete_theme":
                theme = get_object_or_404(SouthlandShowcaseTheme, pk=request.POST.get("theme_id"))
                name = theme.name
                theme.delete()
                messages.success(request, f"{name} was deleted.")
            elif action == "delete_theme_photo":
                photo = get_object_or_404(SouthlandShowcaseThemePhoto, pk=request.POST.get("photo_id"))
                name = photo.theme.name
                photo.delete()
                messages.success(request, f"A photo was removed from {name}.")
            elif action == "add_addon":
                name = request.POST.get("name", "").strip()
                price_label = request.POST.get("price_label", "").strip()
                if not name or not price_label:
                    raise ValueError("Add-on name and price display are required.")
                addon = SouthlandShowcaseAddon(
                    name=name,
                    price_label=price_label,
                    price_from=request.POST.get("price_from") or 0,
                    details=request.POST.get("details", "").strip(),
                    sort_order=(SouthlandShowcaseAddon.objects.order_by("-sort_order").values_list("sort_order", flat=True).first() or 0) + 1,
                )
                image = _validated_image(request.FILES.get("image"))
                if image:
                    for field, value in image.items():
                        setattr(addon, field, value)
                addon.full_clean()
                addon.save()
                messages.success(request, f"{addon.name} was added.")
            elif action == "toggle_addon":
                addon = get_object_or_404(SouthlandShowcaseAddon, pk=request.POST.get("addon_id"))
                addon.is_active = not addon.is_active
                addon.save(update_fields=("is_active", "updated_at"))
                messages.success(request, f"{addon.name} is now {'visible' if addon.is_active else 'hidden'}.")
            elif action == "delete_addon":
                addon = get_object_or_404(SouthlandShowcaseAddon, pk=request.POST.get("addon_id"))
                name = addon.name
                addon.delete()
                messages.success(request, f"{name} was deleted.")
            else:
                raise ValueError("Unknown showcase action.")
    except (ValueError, TypeError, ValidationError) as exc:
        messages.error(request, "; ".join(exc.messages) if isinstance(exc, ValidationError) else str(exc))
    return redirect("southland_showcase_manage")
