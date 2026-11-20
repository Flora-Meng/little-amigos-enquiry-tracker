from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import OuterRef, Prefetch, Q, Subquery
import json
import re

from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils import timezone
from django.views.decorators.http import require_POST
from enquiries.models import Enquiry, Note
from enquiries.services import due_today, overdue

from .authorization import enquiries_visible_to
from .models import (
    Location,
    SouthlandShowcaseAddon,
    SouthlandShowcaseInvite,
    SouthlandShowcaseTheme,
    SouthlandShowcaseThemePhoto,
    ThemeLibraryPhoto,
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
    can_see_party_questions = request.user.role == User.Role.ADMIN or (
        request.user.location
        and request.user.location.code == Location.Code.SOUTHLAND
    )
    party_questions = (
        SouthlandShowcaseInvite.objects.exclude(customer_question="")
        .filter(question_resolved_at__isnull=True)
        .order_by("-choices_submitted_at", "-created_at")[:10]
        if can_see_party_questions
        else SouthlandShowcaseInvite.objects.none()
    )

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
                "party_questions": party_questions,
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
        {
            "cards": cards,
            "recent": recent,
            "status_choices": Enquiry.Status.choices,
            "party_questions": party_questions,
        },
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


@login_required
def theme_library(request):
    if request.user.role == User.Role.STAFF:
        if not request.user.location_id:
            raise Http404
        return redirect("theme_library_location", location_code=request.user.location.code)
    locations = Location.objects.order_by("name")
    return render(request, "accounts/theme_library_hub.html", {"locations": locations})


@login_required
def theme_library_location(request, location_code):
    from party_summaries.models import PartySummary

    location = get_object_or_404(Location, code=location_code)
    if request.user.role == User.Role.STAFF and request.user.location_id != location.id:
        raise Http404
    summary_photos = list(
        PartySummary.objects.filter(location=location, decoration_example__isnull=False)
        .defer("invoice_file", "decoration_example", "decoration_reference")
        .order_by("-party_date", "-updated_at")
    )
    direct_photos = list(
        ThemeLibraryPhoto.objects.filter(location=location)
        .defer("image_data")
        .select_related("created_by")
    )
    for summary in summary_photos:
        summary.library_kind = "summary"
        summary.library_photo_url = reverse("party_summary_decoration", args=(summary.pk,))
        summary.library_theme = summary.theme
        summary.library_description = ""
        summary.library_date = summary.party_date
        summary.library_source_label = summary.get_room_type_display()
        summary.library_owner = summary.owner_name
    for photo in direct_photos:
        photo.library_kind = "direct"
        photo.library_photo_url = reverse(
            "theme_library_direct_photo",
            args=(location.code, photo.pk),
        )
        photo.library_theme = photo.theme
        photo.library_description = photo.description
        photo.library_date = photo.created_at.date()
        photo.library_source_label = "Theme Library upload"
        photo.library_owner = photo.description or (
            f"Added by {photo.created_by.display_name}" if photo.created_by else "Direct upload"
        )
    selection_photos = sorted(
        [*summary_photos, *direct_photos],
        key=lambda photo: photo.updated_at,
        reverse=True,
    )
    search = request.GET.get("search", "").strip()
    photos = selection_photos
    if search:
        search_lower = search.lower()
        photos = [
            photo for photo in photos
            if search_lower in " ".join((
                photo.library_theme or "",
                photo.library_owner or "",
                getattr(photo, "kids_name", "") or "",
                photo.library_description or "",
            )).lower()
        ]
    themes = []
    if location.code == Location.Code.SOUTHLAND:
        themes = list(SouthlandShowcaseTheme.objects.prefetch_related("photos").all())
        for theme in themes:
            theme.admin_photos = list(theme.photos.all())
            for photo in theme.admin_photos:
                photo.preview_url = _theme_photo_url(photo)
    return render(
        request,
        "accounts/theme_library_location.html",
        {
            "location": location,
            "photos": photos,
            "selection_photos": selection_photos,
            "search": search,
            "themes": themes,
            "category_choices": SouthlandShowcaseTheme.Category.choices,
            "can_manage_showcase": request.user.role == User.Role.ADMIN,
            "theme_library_return": reverse(
                "theme_library_location", args=(Location.Code.SOUTHLAND,),
            ),
        },
    )


def _theme_library_location_for_user(request, location_code):
    location = get_object_or_404(Location, code=location_code)
    if request.user.role == User.Role.STAFF and request.user.location_id != location.id:
        raise Http404
    return location


@login_required
def theme_library_direct_photo(request, location_code, photo_id):
    location = _theme_library_location_for_user(request, location_code)
    photo = get_object_or_404(ThemeLibraryPhoto, pk=photo_id, location=location)
    response = HttpResponse(bytes(photo.image_data), content_type=photo.image_content_type)
    response["Content-Disposition"] = f'inline; filename="{photo.image_name}"'
    return response


@login_required
@require_POST
def theme_library_photo_create(request, location_code):
    location = _theme_library_location_for_user(request, location_code)
    theme = request.POST.get("theme", "").strip()
    try:
        image = _validated_image(request.FILES.get("image"))
        if not theme:
            raise ValueError("Theme name is required.")
        if not image:
            raise ValueError("Choose a photo to upload.")
        ThemeLibraryPhoto.objects.create(
            location=location,
            theme=theme,
            description=request.POST.get("description", "").strip(),
            created_by=request.user,
            **image,
        )
        messages.success(request, f"{theme} was added to the Theme Library.")
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("theme_library_location", location_code=location.code)


@login_required
@require_POST
def theme_library_direct_photo_update(request, location_code, photo_id):
    location = _theme_library_location_for_user(request, location_code)
    photo = get_object_or_404(ThemeLibraryPhoto, pk=photo_id, location=location)
    theme = request.POST.get("theme", "").strip()
    try:
        if not theme:
            raise ValueError("Theme name is required.")
        image = _validated_image(request.FILES.get("image"))
        photo.theme = theme
        photo.description = request.POST.get("description", "").strip()
        update_fields = ["theme", "description", "updated_at"]
        if image:
            for field, value in image.items():
                setattr(photo, field, value)
            update_fields.extend(("image_data", "image_name", "image_content_type"))
        photo.save(update_fields=update_fields)
        messages.success(request, f"{theme} was updated.")
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("theme_library_location", location_code=location.code)


@login_required
@require_POST
def theme_library_summary_photo_update(request, location_code, summary_id):
    from party_summaries.models import PartySummary

    location = _theme_library_location_for_user(request, location_code)
    summary = get_object_or_404(
        PartySummary,
        pk=summary_id,
        location=location,
        decoration_example__isnull=False,
    )
    theme = request.POST.get("theme", "").strip()
    try:
        if not theme:
            raise ValueError("Theme name is required.")
        image = _validated_image(request.FILES.get("image"))
        summary.theme = theme
        update_fields = ["theme", "updated_at"]
        if image:
            summary.decoration_example = image["image_data"]
            summary.decoration_example_name = image["image_name"]
            summary.decoration_example_content_type = image["image_content_type"]
            update_fields.extend((
                "decoration_example",
                "decoration_example_name",
                "decoration_example_content_type",
            ))
        summary.save(update_fields=update_fields)
        messages.success(request, f"{theme} was updated in the Theme Library.")
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("theme_library_location", location_code=location.code)


@login_required
@require_POST
def theme_library_direct_photo_remove(request, location_code, photo_id):
    location = _theme_library_location_for_user(request, location_code)
    photo = get_object_or_404(ThemeLibraryPhoto, pk=photo_id, location=location)
    theme = photo.theme
    photo.delete()
    messages.success(request, f"{theme} was removed from the Theme Library.")
    return redirect("theme_library_location", location_code=location.code)


@login_required
@require_POST
def theme_library_photo_remove(request, location_code, summary_id):
    from party_summaries.models import PartySummary

    location = _theme_library_location_for_user(request, location_code)
    summary = get_object_or_404(
        PartySummary,
        pk=summary_id,
        location=location,
        decoration_example__isnull=False,
    )
    summary.decoration_example = None
    summary.decoration_example_name = ""
    summary.decoration_example_content_type = ""
    summary.save(update_fields=(
        "decoration_example",
        "decoration_example_name",
        "decoration_example_content_type",
        "updated_at",
    ))
    messages.success(
        request,
        "The photo was removed from the Theme Library. The Party Summary was not deleted.",
    )
    return redirect("theme_library_location", location_code=location.code)


def southland_party_guide(request, token=None):
    """Public Southland party guide with choice submission for personalised links."""
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
            "tag": "",
            "weekday": 699,
            "weekend": 899,
            "kids": 8,
            "adults": 10,
            "drinks": 1,
            "family_range": "5–8 families",
            "party_time": "10am–12pm or 1pm–3pm",
            "adult_meal_count": 4,
            "room_image": "package_showcase/southland/theme-pages/page-02.jpg",
            "perks": (
                "Single room access",
                "2 hours party time (room hire + playland)",
                "Basic balloon decorations",
                "Number balloon + balloon garland base",
                "Table settings",
                "E-invitation",
                "Party host — greeting guests, birthday cake ceremony and wrap up",
            ),
            "included": (
                "1 mixed fryer platter (50 pcs)",
                "1 seasonal fruit platter",
                "2 pizzas (10-inch each)",
                "1 jug of soft drinks/juice",
                "1 jug of refillable water",
            ),
        },
        {
            "key": "signature",
            "label": "Signature",
            "room": "Double room",
            "tag": "Most popular",
            "weekday": 999,
            "weekend": 1299,
            "kids": 15,
            "adults": 20,
            "drinks": 2,
            "family_range": "8–12 families",
            "party_time": "10am–12pm or 1pm–3pm",
            "adult_meal_count": 9,
            "room_image": "package_showcase/southland/theme-pages/page-03.jpg",
            "perks": (
                "Double room access",
                "2 hours party time (room hire + playland)",
                "Luxury balloon decorations",
                "1 backdrop + 2 cutouts + 2.5m balloon arch",
                "Table settings — balloons on chairs, plates and cutlery",
                "E-invitation",
                "Party host — welcome and assist guests upon arrival",
                "Organised group activities for children",
                "Birthday cake ceremony and wrap up",
                "Exclusive train ride",
            ),
            "included": (
                "1 mixed fryer platter (50 pcs)",
                "1 seasonal fruit platter",
                "4 pizzas (10-inch each)",
                "1 Greek salad bowl or Caesar salad",
                "1 mini burger platter (10 pcs)",
                "1 smoked salmon toast platter (12 pcs) or mushroom toast (vegetarian)",
                "2 jugs of soft drinks/juice",
                "1 jug of refillable water",
            ),
        },
        {
            "key": "ultimate",
            "label": "Ultimate",
            "room": "Triple room",
            "tag": "Best value",
            "weekday": 1899,
            "weekend": 2199,
            "kids": 25,
            "adults": 30,
            "drinks": 6,
            "family_range": "15–25 families",
            "party_time": "10am–12pm or 1pm–3pm",
            "adult_meal_count": 12,
            "room_image": "package_showcase/southland/theme-pages/page-04.jpg",
            "perks": (
                "Triple room access",
                "2 hours party time (room hire + playland)",
                "Premium balloon decorations",
                "2 backdrops + 2–3 cutouts + 3m balloon arch",
                "Table settings — balloons on chairs, plates and cutlery",
                "E-invitation",
                "Party host — welcome and assist guests upon arrival",
                "Organised group activities for children",
                "Birthday cake ceremony and wrap up",
                "20-minute mascot appearance",
                "2 exclusive train rides",
            ),
            "included": (
                "1 mixed fryer platter (50 pcs)",
                "1 seasonal fruit platter",
                "4 pizzas (10-inch each)",
                "1 Greek salad bowl or Caesar salad",
                "1 mini burger platter (10 pcs)",
                "1 taco platter (12 pcs)",
                "1 chicken pesto pasta bowl",
                "1 smoked salmon toast platter (12 pcs) or mushroom toast (vegetarian)",
                "1 sushi platter",
                "6 jugs of soft drinks/juice",
                "1 jug of refillable water",
            ),
        },
        {
            "key": "private",
            "label": "Private",
            "room": "Whole venue hire",
            "tag": "Exclusive",
            "weekday": 2699,
            "weekend": 2999,
            "kids": 35,
            "adults": 40,
            "drinks": 8,
            "family_range": "30–40 families",
            "party_time": "4:30pm–7:30pm",
            "adult_meal_count": 13,
            "room_image": "package_showcase/southland/theme-pages/page-05.jpg",
            "perks": (
                "Whole venue hire",
                "3 hours party time",
                "Ultimate balloon decoration",
                "2 backdrops + 2–3 cutouts + 3.5m balloon arch",
                "Table settings — balloons on chairs, plates and cutlery",
                "E-invitation",
                "Party host — welcome and assist guests upon arrival",
                "Organised group activities for children",
                "Birthday cake ceremony",
                "Enhanced game structure (2 games total)",
                "20-minute mascot appearance",
                "Birthday cake cutting service and wrap up",
                "Party bags for all children (toys and lollies included)",
                "2 exclusive train rides",
            ),
            "included": (
                "1 mixed fryer platter (50 pcs)",
                "1 seasonal fruit platter",
                "4 pizzas (10-inch each)",
                "1 Greek salad bowl or Caesar salad",
                "1 mini burger platter (10 pcs)",
                "1 taco platter (12 pcs)",
                "1 chicken pesto pasta bowl",
                "1 finger sandwich platter (16 pcs)",
                "1 smoked salmon toast platter (12 pcs) or mushroom toast (vegetarian)",
                "1 sushi platter",
                "8 jugs of soft drinks/juice",
                "1 jug of refillable water",
            ),
        },
    )
    for package in packages:
        package["weekday_label"] = f"${package['weekday']:,}"
        package["weekend_label"] = f"${package['weekend']:,}"
        package["deposit"] = 500 if package["key"] in {"essential", "signature"} else 1000
        package["deposit_label"] = f"${package['deposit']:,} deposit"

    kids_meal_choices = (
        "Nuggets and chips",
        "Ham and cheese toastie",
        "Spring rolls and chips (VEG)",
        "Kid spaghetti",
        "Fish finger and chips",
    )

    kids_food_photos = (
        "package_showcase/southland/food/kids/1.png",
        "package_showcase/southland/food/kids/2.png",
    )
    package_food_photos = (
        "package_showcase/southland/food/package/1.png",
        "package_showcase/southland/food/package/2.png",
        "package_showcase/southland/food/package/3.png",
        "package_showcase/southland/food/package/4.png",
        "package_showcase/southland/food/package/5.png",
        "package_showcase/southland/food/package/11.png",
    )

    themes = _southland_theme_catalog()

    addons = list(SouthlandShowcaseAddon.objects.filter(is_active=True))
    addon_options = {
        "Face painting": [
            {"label": "1.5 hours", "price": 330},
            {"label": "2 hours", "price": 380},
        ],
        "Customised cake": [
            {"label": "Tall 6-inch cake", "price": 188},
            {"label": "Tall 8-inch cake", "price": 238},
            {"label": "6+8 two-tier cake", "price": 288},
            {"label": "Tall 6+8 two-tier cake", "price": 368},
        ],
        "Entertainer or mascot": [
            {"label": "1 hour", "price": 380},
            {"label": "2 hours", "price": 580},
        ],
        "Professional photographer": [
            {"label": "1 hour", "price": 200},
            {"label": "2 hours", "price": 380},
        ],
    }
    for addon in addons:
        addon.image_url = _addon_image_url(addon)
        addon.image_urls = _addon_image_urls(addon)
        addon.selection_options = addon_options.get(addon.name, [])
        addon.is_quantity_addon = addon.name == "Party bags"
        if addon.name == "Entertainer or mascot":
            addon.price_label = "1 hour $380 · 2 hours $580"

    if request.method == "POST":
        package_key = request.POST.get("selected_package", "").strip()
        theme_name = request.POST.get("selected_theme", "").strip()
        customer_question = request.POST.get("customer_question", "").strip()
        try:
            selected_addons = json.loads(request.POST.get("selected_addons", "[]"))
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Choose valid add-ons.")

        if package_key not in {package["key"] for package in packages}:
            return HttpResponseBadRequest("Choose a valid package.")
        if theme_name and theme_name not in {theme.name for theme in themes}:
            return HttpResponseBadRequest("Choose a valid theme.")
        if not isinstance(selected_addons, list) or len(selected_addons) > 20:
            return HttpResponseBadRequest("Choose valid add-ons.")
        if len(customer_question) > 2000:
            return HttpResponseBadRequest("Please keep your question under 2,000 characters.")

        if not invite:
            customer_name = request.POST.get("customer_name", "").strip()
            customer_email = request.POST.get("customer_email", "").strip()
            customer_phone = request.POST.get("customer_phone", "").strip()
            if not customer_name or len(customer_name) > 120:
                return HttpResponseBadRequest("Please enter your name.")
            if not customer_question:
                return HttpResponseBadRequest("Please write your question for Flora.")
            if not customer_email and not customer_phone:
                return HttpResponseBadRequest("Please enter an email address or phone number.")
            if customer_email:
                try:
                    validate_email(customer_email)
                except ValidationError:
                    return HttpResponseBadRequest("Please enter a valid email address.")
            if len(customer_phone) > 40:
                return HttpResponseBadRequest("Please enter a valid phone number.")

        valid_addons = set()
        for addon in addons:
            if addon.selection_options:
                valid_addons.update(
                    f"{addon.name} — {option['label']}" for option in addon.selection_options
                )
            elif not addon.is_quantity_addon:
                valid_addons.add(addon.name)
        cleaned_addons = []
        for item in selected_addons:
            if not isinstance(item, str) or len(item) > 160:
                return HttpResponseBadRequest("Choose valid add-ons.")
            party_bag_match = re.fullmatch(r"Party bags × ([1-9][0-9]{0,2})", item)
            if item not in valid_addons and not (
                party_bag_match and int(party_bag_match.group(1)) <= 200
            ):
                return HttpResponseBadRequest("Choose valid add-ons.")
            cleaned_addons.append(item)

        creating_invite = not invite
        if creating_invite:
            invite = SouthlandShowcaseInvite(
                customer_name=customer_name,
                email=customer_email,
                phone=customer_phone,
            )
        invite.selected_package = package_key
        invite.selected_theme = theme_name
        invite.selected_addons = cleaned_addons
        invite.customer_question = customer_question
        invite.question_resolved_at = None
        invite.choices_submitted_at = timezone.now()
        if creating_invite:
            invite.save()
        else:
            invite.save(update_fields=(
                "selected_package",
                "selected_theme",
                "selected_addons",
                "customer_question",
                "question_resolved_at",
                "choices_submitted_at",
            ))
        return redirect(
            f"{reverse('southland_party_guide_invite', kwargs={'token': invite.token})}"
            "?question_sent=1#ask-flora"
        )
    return render(
        request,
        "package_showcase/southland_public.html",
        {
            "packages": packages,
            "themes": themes,
            "addons": addons,
            "invite": invite,
            "question_sent": request.GET.get("question_sent") == "1",
            "kids_food_photos": kids_food_photos,
            "kids_meal_choices": kids_meal_choices,
            "package_food_photos": package_food_photos,
        },
    )


@login_required
@require_POST
def southland_question_resolve(request, invite_id):
    can_handle = request.user.role == User.Role.ADMIN or (
        request.user.location
        and request.user.location.code == Location.Code.SOUTHLAND
    )
    if not can_handle:
        raise PermissionDenied("Only the Southland team can handle these questions.")
    invite = get_object_or_404(
        SouthlandShowcaseInvite.objects.exclude(customer_question=""),
        pk=invite_id,
    )
    invite.question_resolved_at = timezone.now()
    invite.save(update_fields=("question_resolved_at",))
    messages.success(request, f"{invite.customer_name}'s question was marked as handled.")
    return redirect("dashboard")


def _southland_theme_catalog():
    themes = list(
        SouthlandShowcaseTheme.objects.filter(is_active=True).prefetch_related(
            Prefetch("photos", queryset=SouthlandShowcaseThemePhoto.objects.order_by("sort_order", "id"))
        )
    )
    for theme in themes:
        theme.photo_urls = [_theme_photo_url(photo) for photo in theme.photos.all()]
        theme.cover_url = theme.photo_urls[0] if theme.photo_urls else ""
        theme.search_text = f"{theme.name} {theme.search_terms}".lower()
    return themes


def southland_theme_list(request):
    """A permanent public link that always shows the current Southland themes."""
    return render(
        request,
        "package_showcase/southland_theme_list.html",
        {"themes": _southland_theme_catalog()},
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
    addon_examples = {
        "Face painting": ("package_showcase/canberra/addons/face-painting.jpg",),
        "Customised cake": (
            "package_showcase/southland/addons/cake1.png",
            "package_showcase/southland/addons/cake2.png",
        ),
        "Entertainer or mascot": (
            "package_showcase/canberra/addons/entertainer-1.jpg",
            "package_showcase/canberra/addons/entertainer-2.jpg",
            "package_showcase/canberra/addons/mascot-1.jpg",
            "package_showcase/canberra/addons/mascot-2.jpg",
        ),
        "Professional photographer": (
            "package_showcase/southland/addons/photographer.png",
        ),
        "Party bags": ("package_showcase/southland/addons/partybags.png",),
    }
    paths = addon_examples.get(addon.name)
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
    from party_summaries.models import PartySummary

    themes = list(SouthlandShowcaseTheme.objects.prefetch_related("photos").all())
    for theme in themes:
        theme.admin_photos = list(theme.photos.all())
        for photo in theme.admin_photos:
            photo.preview_url = _theme_photo_url(photo)
    addons = list(SouthlandShowcaseAddon.objects.all())
    for addon in addons:
        addon.image_url = _addon_image_url(addon)
    submitted_choices = list(
        SouthlandShowcaseInvite.objects.exclude(choices_submitted_at__isnull=True)
        .select_related("created_by")
        .order_by("-choices_submitted_at")[:50]
    )
    library_photos = list(
        PartySummary.objects.filter(
            location__code=Location.Code.SOUTHLAND,
            decoration_example__isnull=False,
        )
        .select_related("location")
        .prefetch_related("southland_showcase_photos__theme")
        .order_by("-party_date", "-updated_at")
    )
    for summary in library_photos:
        summary.library_photo_url = reverse("party_summary_decoration", args=(summary.pk,))
        summary.applied_theme_names = [
            photo.theme.name for photo in summary.southland_showcase_photos.all()
        ]
    return render(
        request,
        "accounts/southland_showcase_manage.html",
        {
            "themes": themes,
            "addons": addons,
            "library_photos": library_photos,
            "submitted_choices": submitted_choices,
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
            elif action == "apply_summary_photo":
                from party_summaries.models import PartySummary

                theme = get_object_or_404(SouthlandShowcaseTheme, pk=request.POST.get("theme_id"))
                source_type, separator, source_id = request.POST.get("library_photo", "").partition(":")
                if not separator or source_type not in {"summary", "direct"}:
                    raise ValueError("Choose a Theme Library photo.")
                if source_type == "summary":
                    summary = get_object_or_404(
                        PartySummary,
                        pk=source_id,
                        location__code=Location.Code.SOUTHLAND,
                        decoration_example__isnull=False,
                    )
                    SouthlandShowcaseThemePhoto.objects.filter(
                        theme=theme, source_summary=summary,
                    ).delete()
                    photo_values = {
                        "source_summary": summary,
                        "image_data": bytes(summary.decoration_example),
                        "image_name": summary.decoration_example_name,
                        "image_content_type": summary.decoration_example_content_type,
                    }
                else:
                    library_photo = get_object_or_404(
                        ThemeLibraryPhoto,
                        pk=source_id,
                        location__code=Location.Code.SOUTHLAND,
                    )
                    photo_values = {
                        "image_data": bytes(library_photo.image_data),
                        "image_name": library_photo.image_name,
                        "image_content_type": library_photo.image_content_type,
                    }
                SouthlandShowcaseThemePhoto.objects.create(
                    theme=theme,
                    sort_order=theme.photos.count() + 1,
                    **photo_values,
                )
                messages.success(request, f"The Theme Library photo was added to {theme.name}.")
            elif action == "create_theme_from_summary":
                from party_summaries.models import PartySummary

                summary = get_object_or_404(
                    PartySummary,
                    pk=request.POST.get("summary_id"),
                    location__code=Location.Code.SOUTHLAND,
                    decoration_example__isnull=False,
                )
                name = request.POST.get("name", "").strip() or summary.theme.strip()
                if not name:
                    raise ValueError("Enter a name for the new theme.")
                theme = SouthlandShowcaseTheme.objects.create(
                    name=name,
                    category=SouthlandShowcaseTheme.Category.FAVOURITES,
                    sort_order=(SouthlandShowcaseTheme.objects.order_by("-sort_order").values_list("sort_order", flat=True).first() or 0) + 1,
                )
                SouthlandShowcaseThemePhoto.objects.create(
                    theme=theme,
                    source_summary=summary,
                    image_data=bytes(summary.decoration_example),
                    image_name=summary.decoration_example_name,
                    image_content_type=summary.decoration_example_content_type,
                )
                messages.success(request, f"{theme.name} was created from the Party Summary photo.")
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
    return_to = request.POST.get("next", "")
    theme_library_url = reverse(
        "theme_library_location", args=(Location.Code.SOUTHLAND,),
    )
    if return_to == theme_library_url:
        return redirect(f"{theme_library_url}#customer-theme-catalogue")
    return redirect("southland_showcase_manage")
