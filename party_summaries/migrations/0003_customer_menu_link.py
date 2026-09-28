import uuid

from django.db import migrations, models


def populate_customer_menu_tokens(apps, schema_editor):
    PartySummary = apps.get_model("party_summaries", "PartySummary")
    for summary in PartySummary.objects.filter(customer_menu_token__isnull=True).iterator():
        summary.customer_menu_token = uuid.uuid4()
        summary.save(update_fields=("customer_menu_token",))


class Migration(migrations.Migration):
    dependencies = [("party_summaries", "0002_decoration_example")]
    operations = [
        migrations.AddField(
            model_name="partysummary",
            name="customer_menu_token",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.RunPython(populate_customer_menu_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="partysummary",
            name="customer_menu_token",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AddField(
            model_name="partysummary",
            name="customer_menu_submitted_at",
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="partysummary",
            name="dietary_requirements",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="partysummary",
            name="adult_food_avoid",
            field=models.TextField(blank=True),
        ),
    ]
