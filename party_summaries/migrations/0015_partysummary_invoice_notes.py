from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("party_summaries", "0014_partysummary_actual_balance_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="partysummary",
            name="invoice_notes",
            field=models.TextField(blank=True),
        ),
    ]
