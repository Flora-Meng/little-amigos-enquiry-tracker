from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from accounts.models import Location, User

from .forms import (
    ADULT_FRYER_CHOICES,
    ADULT_MAIN_CHOICES,
    ADULT_PASTA_CHOICES,
    ADULT_STARTER_CHOICES,
    EXTRA_MENU_OPTIONS,
    KIDS_HOT_FOOD_CHOICES,
    PRIVATE_SANDWICH_CHOICES,
    TRIPLE_BURGER_CHOICES,
    TRIPLE_FRYER_CHOICES,
    TRIPLE_PASTA_CHOICES,
    TRIPLE_PIZZA_CHOICES,
    TRIPLE_SALAD_CHOICES,
    TRIPLE_SUSHI_CHOICES,
    TRIPLE_TACO_CHOICES,
    TRIPLE_TOAST_CHOICES,
    CustomerMenuForm,
    PartySummaryForm,
    menu_formsets,
)
from .models import PartyMenuItem, PartySummary
from .pdf import build_party_summary_pdf


ADULT_MENU_OPTIONS = [
    "Drink", "Water", "Mix Fryer platter", "Mix Fryer platter (Vege)", "Fruit Platter",
    "Mini burger 10pcs (Pork)", "Mini burger 10pcs (Prawn)", "Mini burger 10pcs (Vege)",
    "Finger Sandwiches 16pcs (Tuna)", "Finger Sandwiches 16pcs (Egg)",
    "Finger Sandwiches 16pcs (Cheese & Tomato)", "Japanese sushi platter (assorted)",
    "Japanese sushi platter (vege)", "Taco platter 12pcs (Karaage chicken)",
    "Taco platter 12pcs (Fish)", "Taco platter 12pcs (Black Beans)", "Pizza (Margherita)",
    "Pizza (Pepperoni)", "Pizza (Vege)", "Pizza (Cheese)", "Smoked Salmon Avocado Toast 10pcs",
    "Millennial Mushroom Toast 10pcs", "Ham and Cheese Toast 10pcs", "Cheese Toast 10pcs",
    "Chicken Pesto Pasta Bowl", "Pesto Pasta Bowl without chicken", "Greek Salad Bowl",
    "Rice paper roll - 12 pcs (Tofu)", "Rice paper roll - 12 pcs (Prawn)", "Caesar chicken salad",
    "Mixed Grilled platter", "Grilled salmon platter 10pcs", "Lamb Souvlaki platter",
    "Grilled chicken breast platter", "Grilled Beef Skewer platter 10pcs", "Grilled Pork ribs platter",
    "Grilled Lobster platter", "Beef Ragu Spaghetti", "Creamy Prawn Linguine",
    "Greek Salad Bowl with Grilled chicken", "Cocktail Prawn Salad", "Chips Tray", "Spring rolls tray",
    "Karaage Chicken Tray 15pcs", "Wedges & Chips Tray", "Calamari & Chips Tray", "Nuggets Tray",
    "Chicken Schnitzel Wrap platter 10 halves", "Spaghetti Bolognese", "Sweet potato chips tray",
    "Mini Burger Sliders (Beef)", "Mini Burger Sliders (Chicken)", "Air Fryer Platter",
    "Wrap Box 10 halves", "Rice Paper Roll", "Pizza (BBQ Chicken)", "Tomato Bruschetta (10 pcs)",
    "Skewer Box", "Dip Platter", "Caesar salad", "Greek salad", "sushi platter",
    "fruit platter (medium)", "3-tier dessert",
]
KIDS_MENU_OPTIONS = [
    "Nuggets & Chips", "Fish fingers & Chips", "Ham & Cheese Toast", "Spring rolls & Chips",
    "Kid spaghetti", "Tomato & Cheese Toast", "Mini cupcakes", "Yogurt berries smoothie",
]


def summaries_visible_to(user):
    queryset = PartySummary.objects.select_related("location", "created_by").annotate(
        extra_food_total_value=Coalesce(
            Sum("menu_items__amount", filter=Q(menu_items__category=PartyMenuItem.Category.EXTRA)),
            Value(Decimal("0.00")), output_field=DecimalField(max_digits=10, decimal_places=2),
        )
    )
    if user.role == User.Role.ADMIN:
        return queryset
    if user.role == User.Role.STAFF and user.location_id:
        return queryset.filter(location_id=user.location_id)
    return queryset.none()


def _visible_or_404(user, summary_id):
    return get_object_or_404(summaries_visible_to(user), id=summary_id)


def _menu_initial(summary=None):
    if summary is None:
        return {"adult": [{"quantity": "2 Jar", "item": "Drink"}, {"quantity": "1 Jar", "item": "Water"}], "kids": [], "extra": []}
    result = {"adult": [], "kids": [], "extra": []}
    for item in summary.menu_items.all():
        row = {"quantity": item.quantity, "item": item.item, "notes": item.notes}
        if item.category == PartyMenuItem.Category.EXTRA:
            row["amount"] = item.amount
        result[item.category].append(row)
    return result


def _save_menu_items(summary, formsets):
    summary.menu_items.all().delete()
    categories = (("adult_formset", PartyMenuItem.Category.ADULT), ("kids_formset", PartyMenuItem.Category.KIDS), ("extra_formset", PartyMenuItem.Category.EXTRA))
    rows = []
    for key, category in categories:
        for position, form in enumerate(formsets[key]):
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue
            item = (form.cleaned_data.get("item") or "").strip()
            if not item:
                continue
            rows.append(PartyMenuItem(summary=summary, category=category,
                quantity=(form.cleaned_data.get("quantity") or "").strip(), item=item,
                notes=(form.cleaned_data.get("notes") or "").strip(),
                amount=form.cleaned_data.get("amount") or Decimal("0.00"), position=position))
    PartyMenuItem.objects.bulk_create(rows)


def _save_decoration_example(summary, form):
    if form.cleaned_data.get("remove_decoration_example"):
        summary.decoration_example = None
        summary.decoration_example_name = ""
        summary.decoration_example_content_type = ""
    upload = form.cleaned_data.get("decoration_example_upload")
    if upload:
        summary.decoration_example = upload.read()
        summary.decoration_example_name = upload.name[:255]
        summary.decoration_example_content_type = upload.content_type
    summary.save(update_fields=(
        "decoration_example", "decoration_example_name", "decoration_example_content_type", "updated_at",
    ))


@login_required
def party_summary_list(request):
    summaries = summaries_visible_to(request.user)
    search = request.GET.get("search", "").strip()
    party_date = request.GET.get("party_date", "").strip()
    if search:
        summaries = summaries.filter(Q(owner_name__icontains=search) | Q(owner_number__icontains=search)
            | Q(kids_name__icontains=search) | Q(theme__icontains=search) | Q(location__name__icontains=search))
    if party_date:
        summaries = summaries.filter(party_date=party_date)
    summaries = summaries.order_by("-party_date", "-updated_at")
    return render(request, "party_summaries/list.html", {"summaries": summaries,
        "result_count": summaries.count(), "search": search, "party_date": party_date})


def _form_context(form, formsets, summary=None, request=None):
    package_catalog = {}
    for location_code in (Location.Code.SOUTHLAND, Location.Code.CANBERRA):
        prices = PartySummary.package_prices_for_location(location_code)
        package_catalog[str(location_code)] = [
            {"value": str(value), "label": label, "price": str(prices[value])}
            for value, label in PartySummary.package_choices_for_location(location_code)
        ]
    context = {"form": form, "summary": summary, **formsets, "adult_menu_options": ADULT_MENU_OPTIONS,
        "kids_menu_options": KIDS_MENU_OPTIONS,
        "package_catalog": package_catalog,
        "location_codes": {str(location.id): location.code for location in Location.objects.all()},
        "default_package_location": getattr(form, "package_location_code", Location.Code.SOUTHLAND)}
    if summary is not None and request is not None:
        context["customer_menu_url"] = request.build_absolute_uri(
            reverse("customer_menu", args=(summary.customer_menu_token,))
        )
    return context


@login_required
@transaction.atomic
def party_summary_create(request):
    if request.method == "POST":
        form = PartySummaryForm(request.POST, request.FILES, user=request.user)
        formsets = menu_formsets(data=request.POST)
        if form.is_valid() and all(formset.is_valid() for formset in formsets.values()):
            summary = form.save(commit=False)
            if request.user.role == User.Role.STAFF:
                if not request.user.location_id:
                    raise Http404
                summary.location = request.user.location
            summary.created_by = request.user
            summary.save()
            _save_menu_items(summary, formsets)
            _save_decoration_example(summary, form)
            messages.success(request, f"Party summary for {summary.owner_name} was saved.")
            if request.POST.get("action") == "download":
                return redirect("party_summary_pdf", summary_id=summary.id)
            return redirect("party_summary_list")
    else:
        form = PartySummaryForm(user=request.user)
        formsets = menu_formsets(initial=_menu_initial())
    return render(request, "party_summaries/form.html", _form_context(form, formsets, request=request))


@login_required
@transaction.atomic
def party_summary_edit(request, summary_id):
    summary = _visible_or_404(request.user, summary_id)
    if request.method == "POST":
        form = PartySummaryForm(request.POST, request.FILES, instance=summary, user=request.user)
        formsets = menu_formsets(data=request.POST, editing=True)
        if form.is_valid() and all(formset.is_valid() for formset in formsets.values()):
            updated = form.save(commit=False)
            if request.user.role == User.Role.STAFF:
                updated.location = request.user.location
            updated.save()
            _save_menu_items(updated, formsets)
            _save_decoration_example(updated, form)
            messages.success(request, "Party summary updated.")
            if request.POST.get("action") == "download":
                return redirect("party_summary_pdf", summary_id=updated.id)
            return redirect("party_summary_list")
    else:
        form = PartySummaryForm(instance=summary, user=request.user)
        formsets = menu_formsets(initial=_menu_initial(summary), editing=True)
    return render(request, "party_summaries/form.html", _form_context(form, formsets, summary, request))


def _choice_values(choices):
    return {value for value, _label in choices}


def _customer_menu_initial(summary):
    initial = {
        "party_date": summary.party_date,
        "party_time": summary.party_time,
        "owner_name": summary.owner_name,
        "owner_number": summary.owner_number,
        "room_type": summary.room_type if summary.room_type in {
            PartySummary.RoomType.SINGLE,
            PartySummary.RoomType.DOUBLE,
            PartySummary.RoomType.TRIPLE,
            PartySummary.RoomType.PRIVATE,
        } else PartySummary.RoomType.DOUBLE,
        "kids_count": summary.kids_count or 1,
        "adults_count": summary.adults_count,
        "dietary_requirements": summary.dietary_requirements,
        "adult_food_avoid": summary.adult_food_avoid,
    }
    if summary.food_ready.lower().startswith("ready 30") or summary.food_ready.lower().startswith("30 min"):
        initial["food_ready_choice"] = "after_30"
    elif summary.food_ready:
        initial["food_ready_choice"] = "earlier"
        initial["food_ready_time"] = _parse_time_value(summary.food_ready)
    else:
        initial["food_ready_choice"] = "after_30"
    adult_rows = list(summary.menu_items.filter(category=PartyMenuItem.Category.ADULT))
    adult_items = {item.item for item in adult_rows}
    adult_by_name = {item.item: item for item in adult_rows}
    kids_items = list(summary.menu_items.filter(category=PartyMenuItem.Category.KIDS))
    for field, choices in (
        ("adult_fryer", ADULT_FRYER_CHOICES),
        ("adult_starter", ADULT_STARTER_CHOICES),
        ("adult_pasta", ADULT_PASTA_CHOICES),
    ):
        initial[field] = next((value for value in _choice_values(choices) if value in adult_items), "")
    if any(item.startswith("Pizza (") for item in adult_items):
        initial["adult_main"] = "__four_pizzas__"
    else:
        initial["adult_main"] = next((value for value in _choice_values(ADULT_MAIN_CHOICES) if value in adult_items), "")

    for field, choices in (
        ("triple_fryer", TRIPLE_FRYER_CHOICES),
        ("triple_salad", TRIPLE_SALAD_CHOICES),
        ("triple_burger", TRIPLE_BURGER_CHOICES),
        ("triple_taco", TRIPLE_TACO_CHOICES),
        ("triple_pasta", TRIPLE_PASTA_CHOICES),
        ("triple_toast", TRIPLE_TOAST_CHOICES),
        ("triple_sushi", TRIPLE_SUSHI_CHOICES),
        ("private_sandwich", PRIVATE_SANDWICH_CHOICES),
    ):
        value = next((choice for choice in _choice_values(choices) if choice in adult_items), "")
        initial[field] = value
        if value and value in adult_by_name:
            initial[f"{field}_note"] = adult_by_name[value].notes
    pizza_names = {
        "Pizza (Margherita, 10-inch)": "Pizza (Margherita)",
        "Pizza (Pepperoni, 10-inch)": "Pizza (Pepperoni)",
        "Pizza (Vegetarian, 10-inch)": "Pizza (Vegetarian)",
        "Pizza (Cheese, 10-inch)": "Pizza (Cheese)",
    }
    for index, (pizza, _label) in enumerate(TRIPLE_PIZZA_CHOICES):
        row = adult_by_name.get(pizza) or adult_by_name.get(pizza_names[pizza])
        if row:
            initial[f"triple_pizza_{index}_qty"] = int(row.quantity) if row.quantity.isdigit() else 0
            initial["triple_pizza_note"] = row.notes
    fruit = adult_by_name.get("Seasonal fruit platter")
    drinks = adult_by_name.get("Soft drinks / juice") or adult_by_name.get("Refillable water")
    if fruit:
        initial["triple_fruit_note"] = fruit.notes
    if drinks:
        initial["triple_drinks_note"] = drinks.notes

    kids_by_name = {item.item: item for item in kids_items}
    for prefix, choices in (("kids_hot", KIDS_HOT_FOOD_CHOICES),):
        for index, (value, _label) in enumerate(choices):
            item = kids_by_name.get(value)
            if item:
                initial[f"{prefix}_{index}_selected"] = True
                initial[f"{prefix}_{index}_qty"] = int(item.quantity) if item.quantity.isdigit() else None
    extra_by_name = {
        item.item: item for item in summary.menu_items.filter(category=PartyMenuItem.Category.EXTRA)
    }
    for index, (name, _price) in enumerate(EXTRA_MENU_OPTIONS):
        item = extra_by_name.get(name)
        if item:
            initial[f"extra_{index}_selected"] = True
            initial[f"extra_{index}_qty"] = int(item.quantity) if item.quantity.isdigit() else 1
    return initial


def _parse_time_value(value):
    from datetime import datetime

    cleaned = value.lower().replace("ready at", "").strip()
    for pattern in ("%H:%M", "%I:%M%p", "%I:%M %p"):
        try:
            return datetime.strptime(cleaned, pattern).time()
        except ValueError:
            continue
    return None


def _customer_menu_deadline(summary):
    matches = list(re.finditer(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", summary.party_time, re.IGNORECASE))
    hour = 0
    minute = 0
    meridiem = None
    if matches:
        first = matches[0]
        hour = int(first.group(1))
        minute = int(first.group(2) or 0)
        meridiem = first.group(3)
        if not meridiem:
            meridiem = next((match.group(3) for match in matches[1:] if match.group(3)), None)
        if meridiem:
            hour %= 12
            if meridiem.lower() == "pm":
                hour += 12
        if hour > 23 or minute > 59:
            hour = minute = 0
    party_start = timezone.make_aware(
        datetime.combine(summary.party_date, datetime.min.time()).replace(hour=hour, minute=minute),
        timezone.get_current_timezone(),
    )
    return party_start - timedelta(hours=72)


def _save_customer_menu(summary, cleaned):
    summary.party_date = cleaned["party_date"]
    summary.party_time = cleaned["party_time"]
    summary.owner_name = cleaned["owner_name"]
    summary.owner_number = cleaned["owner_number"]
    summary.room_type = cleaned["room_type"]
    summary.kids_count = cleaned["kids_count"]
    summary.adults_count = cleaned["adults_count"]
    summary.dietary_requirements = cleaned.get("dietary_requirements", "")
    summary.adult_food_avoid = cleaned.get("adult_food_avoid", "")
    if cleaned["food_ready_choice"] == "after_30":
        summary.food_ready = "Ready 30 minutes after the party starts"
    else:
        summary.food_ready = f"Ready at {cleaned['food_ready_time'].strftime('%-I:%M %p')}"
    summary.customer_menu_submitted_at = timezone.now()
    summary.save(update_fields=(
        "party_date", "party_time", "owner_name", "owner_number", "room_type",
        "kids_count", "adults_count", "dietary_requirements", "adult_food_avoid",
        "food_ready", "customer_menu_submitted_at", "updated_at",
    ))

    rows = []
    room_type = cleaned["room_type"]
    adult_items = [
        ("1 platter (50pcs)", cleaned["triple_fryer"], cleaned.get("triple_fryer_note", "")),
        ("1 platter", "Seasonal fruit platter", cleaned.get("triple_fruit_note", "")),
    ]
    for index, (pizza, _label) in enumerate(TRIPLE_PIZZA_CHOICES):
        quantity = cleaned.get(f"triple_pizza_{index}_qty") or 0
        if quantity:
            adult_items.append((str(quantity), pizza, cleaned.get("triple_pizza_note", "")))
    if room_type != PartySummary.RoomType.SINGLE:
        adult_items.extend((
            ("1 bowl", cleaned["triple_salad"], cleaned.get("triple_salad_note", "")),
            ("1 platter (10pcs)", cleaned["triple_burger"], cleaned.get("triple_burger_note", "")),
        ))
    if room_type in {PartySummary.RoomType.TRIPLE, PartySummary.RoomType.PRIVATE}:
        adult_items.extend((
            ("1 platter (12pcs)", cleaned["triple_taco"], cleaned.get("triple_taco_note", "")),
            ("1 bowl", cleaned["triple_pasta"], cleaned.get("triple_pasta_note", "")),
        ))
    if room_type == PartySummary.RoomType.PRIVATE:
        adult_items.append((
            "1 platter (16pcs)", cleaned["private_sandwich"], cleaned.get("private_sandwich_note", ""),
        ))
    if room_type != PartySummary.RoomType.SINGLE:
        adult_items.append(
            ("1 platter (12pcs)", cleaned["triple_toast"], cleaned.get("triple_toast_note", "")),
        )
    if room_type in {PartySummary.RoomType.TRIPLE, PartySummary.RoomType.PRIVATE}:
        adult_items.append(
            ("1 platter", cleaned["triple_sushi"], cleaned.get("triple_sushi_note", "")),
        )
    drink_count = {
        PartySummary.RoomType.SINGLE: 1,
        PartySummary.RoomType.DOUBLE: 2,
        PartySummary.RoomType.TRIPLE: 6,
        PartySummary.RoomType.PRIVATE: 8,
    }[room_type]
    drink_quantity = "1 jug" if drink_count == 1 else f"{drink_count} jugs"
    adult_items.extend((
        (drink_quantity, "Soft drinks / juice", cleaned.get("triple_drinks_note", "")),
        ("1 jug", "Refillable water", ""),
    ))
    for position, (quantity, item, notes) in enumerate(adult_items):
        rows.append(PartyMenuItem(summary=summary, category=PartyMenuItem.Category.ADULT,
            quantity=quantity, item=item, notes=notes, position=position))

    kids_items = []
    for prefix, choices in (("kids_hot", KIDS_HOT_FOOD_CHOICES),):
        for index, (item, _label) in enumerate(choices):
            if cleaned.get(f"{prefix}_{index}_selected"):
                kids_items.append((str(cleaned[f"{prefix}_{index}_qty"]), item))
    kids_items.append((str(cleaned["kids_count"]), "Kids' size drink"))
    for position, (quantity, item) in enumerate(kids_items):
        rows.append(PartyMenuItem(summary=summary, category=PartyMenuItem.Category.KIDS,
            quantity=quantity, item=item, position=position))

    for index, (item, price) in enumerate(EXTRA_MENU_OPTIONS):
        if cleaned.get(f"extra_{index}_selected"):
            quantity = cleaned[f"extra_{index}_qty"]
            rows.append(PartyMenuItem(summary=summary, category=PartyMenuItem.Category.EXTRA,
                quantity=str(quantity), item=item, amount=Decimal(price) * quantity, position=index))
    summary.menu_items.all().delete()
    PartyMenuItem.objects.bulk_create(rows)


def _no_store(response):
    response["Cache-Control"] = "no-store, private"
    response["Referrer-Policy"] = "no-referrer"
    return response


# This anonymous form is protected by its unguessable per-party bearer token.
# Some embedded/in-app browsers submit it with Origin: null, which Django's
# origin check rejects even when the rendered CSRF token is valid.
@csrf_exempt
@require_http_methods(["GET", "POST"])
@transaction.atomic
def customer_menu(request, token):
    queryset = PartySummary.objects.select_related("location")
    if request.method == "POST":
        queryset = queryset.select_for_update()
    summary = get_object_or_404(queryset, customer_menu_token=token)
    menu_deadline = _customer_menu_deadline(summary)
    menu_locked = timezone.now() >= menu_deadline
    locked_submit_attempt = request.method == "POST" and menu_locked
    if request.method == "POST" and not menu_locked:
        form = CustomerMenuForm(request.POST, venue_code=summary.location.code)
        if form.is_valid():
            _save_customer_menu(summary, form.cleaned_data)
            return redirect("customer_menu_thanks", token=summary.customer_menu_token)
    else:
        form = CustomerMenuForm(initial=_customer_menu_initial(summary), venue_code=summary.location.code)
    response = render(request, "party_summaries/customer_menu.html", {
        "summary": summary,
        "form": form,
        "extra_menu_options": EXTRA_MENU_OPTIONS,
        "menu_deadline": menu_deadline,
        "menu_locked": menu_locked,
        "locked_submit_attempt": locked_submit_attempt,
    })
    return _no_store(response)


@require_http_methods(["GET"])
def customer_menu_thanks(request, token):
    summary = get_object_or_404(PartySummary.objects.select_related("location"), customer_menu_token=token)
    return _no_store(render(request, "party_summaries/customer_menu_thanks.html", {"summary": summary}))


@login_required
def party_summary_delete(request, summary_id):
    summary = _visible_or_404(request.user, summary_id)
    if request.method == "POST":
        owner_name = summary.owner_name
        summary.delete()
        messages.success(request, f"Party summary for {owner_name} was deleted.")
        return redirect("party_summary_list")
    return render(request, "party_summaries/delete.html", {"summary": summary})


@login_required
def party_summary_decoration(request, summary_id):
    summary = _visible_or_404(request.user, summary_id)
    if not summary.decoration_example:
        raise Http404
    response = FileResponse(
        BytesIO(bytes(summary.decoration_example)),
        content_type=summary.decoration_example_content_type,
        filename=summary.decoration_example_name or "decoration-example",
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
def party_summary_pdf(request, summary_id):
    summary = _visible_or_404(request.user, summary_id)
    summary = PartySummary.objects.prefetch_related("menu_items").get(id=summary.id)
    pdf_buffer = build_party_summary_pdf(summary)
    filename = f"party-summary-{summary.party_date.isoformat()}-{summary.owner_name}".lower()
    filename = "".join(character if character.isalnum() or character in "-_" else "-" for character in filename)
    response = FileResponse(pdf_buffer, content_type="application/pdf", as_attachment=True, filename=f"{filename}.pdf")
    return response
