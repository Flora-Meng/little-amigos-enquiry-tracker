import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("party_summaries", "0008_partysummary_voucher_menu_notes"),
    ]

    operations = [
        migrations.CreateModel(
            name="PartyBillItem",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=200)),
                ("amount", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("position", models.PositiveSmallIntegerField(default=0)),
                ("summary", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="bill_items", to="party_summaries.partysummary")),
            ],
            options={
                "db_table": "party_bill_items",
                "ordering": ("position", "id"),
            },
        ),
    ]
