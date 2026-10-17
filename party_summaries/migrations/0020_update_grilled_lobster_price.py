from decimal import Decimal
import re

from django.db import migrations


def _quantity(value):
    match = re.match(r"\s*(\d+(?:\.\d+)?)", value or "")
    return Decimal(match.group(1)) if match else Decimal("1")


def update_grilled_lobster_price(apps, schema_editor):
    PartyMenuItem = apps.get_model("party_summaries", "PartyMenuItem")
    rows = PartyMenuItem.objects.filter(item__iexact="Grilled Lobster platter")
    for row in rows.iterator():
        if row.category == "extra":
            row.amount = Decimal("388.00") * _quantity(row.quantity)
        else:
            row.amount = Decimal("388.00")
        row.save(update_fields=("amount",))


class Migration(migrations.Migration):
    dependencies = [
        ("party_summaries", "0019_partyintakelink_room_type"),
    ]

    operations = [
        migrations.RunPython(update_grilled_lobster_price, migrations.RunPython.noop),
    ]
