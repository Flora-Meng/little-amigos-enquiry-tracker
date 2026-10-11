from decimal import Decimal
import re

from django.db import migrations


PRICE_GROUPS = {
    "88.00": (
        "Mixed fryer platter (assorted)", "Mixed fryer platter (vege)",
        "Japanese sushi platter (assorted)", "Japanese sushi platter (vege)",
        "Lamb Souvlaki platter", "Grilled chicken breast platter",
        "Grilled Beef Skewer platter", "Grilled Pork ribs platter", "Grilled Lobster platter",
    ),
    "75.00": (
        "Mini burger sliders 10pcs (Pork)", "Mini burger sliders 10pcs (Prawn)",
        "Mini burger sliders 10pcs (Vege)", "Mini burger sliders 10pcs (Chicken)",
        "Mini burger sliders 10pcs (Beef)",
    ),
    "68.00": (
        "Taco platter 12pcs (Karaage chicken)", "Taco platter 12pcs (Fish)",
        "Taco platter 12pcs (Black Beans)", "Chicken pesto pasta bowl",
        "Pesto pasta bowl without chicken", "Beef Bolognese Spaghetti", "Creamy Prawn Linguine",
    ),
    "65.00": (
        "Finger Sandwiches 16pcs (Tuna)", "Finger Sandwiches 16pcs (Eggs)",
        "Finger Sandwiches 16pcs (Cheese & Tomato)", "Chicken Schnitzel Wrap platter 10 halves",
    ),
    "48.00": ("Greek Salad Bowl with Grilled chicken", "Spring rolls tray", "Karaage Chicken Tray 15pcs"),
    "45.00": ("Smoked Salmon Avocado Toast 10pcs", "Millennial Mushroom Toast 10pcs"),
    "38.00": ("Greek Salad Bowl", "Chips Tray", "Nuggets Tray", "Wedges & Chips Tray", "Calamari & Chips Tray"),
    "35.00": ("Ham and Cheese Toast 10pcs", "Cheese Toast 10pcs"),
    "19.00": ("Pizza (Cheese)", "Pizza (Vege)", "Pizza (Margherita)", "Pizza (Pepperoni)"),
    "128.00": ("Mixed Grilled Platter", "Grilled Salmon Platter"),
    "78.00": ("Fruit Platter",),
    "96.00": ("Cocktail Prawn Salad",),
}


def normalise(value):
    value = (value or "").casefold().replace("vegetarian", "vege")
    return " ".join(re.findall(r"[a-z0-9]+", value))


UNIT_PRICES = {
    normalise(name): Decimal(price)
    for price, names in PRICE_GROUPS.items()
    for name in names
}


def fix_extra_food_line_totals(apps, schema_editor):
    PartyMenuItem = apps.get_model("party_summaries", "PartyMenuItem")
    for item in PartyMenuItem.objects.filter(category="extra").iterator():
        match = re.match(r"\s*(\d+(?:\.\d+)?)", item.quantity or "")
        quantity = Decimal(match.group(1)) if match else Decimal("1")
        unit_price = UNIT_PRICES.get(normalise(item.item))
        if quantity > 1 and unit_price is not None and item.amount == unit_price:
            item.amount = unit_price * quantity
            item.save(update_fields=("amount",))


class Migration(migrations.Migration):
    dependencies = [
        ("party_summaries", "0015_partysummary_invoice_notes"),
    ]

    operations = [
        migrations.RunPython(fix_extra_food_line_totals, migrations.RunPython.noop),
    ]
